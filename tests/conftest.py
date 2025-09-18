import os
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture(scope="function")
def timestamp_str():
    return datetime.now().strftime(r"%Y-%m-%d %H:%M:%S:%f")


def _get_test_database_url() -> str:
    """Get database URL for testing based on environment."""
    if os.getenv("TEST_DATABASE") == "postgresql":
        # Use a test-specific PostgreSQL database
        base_url = os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/savt"
        )

        # For parallel tests, use unique database name per worker
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")

        # Replace only the database name at the end of the URL
        if base_url.endswith("/savt"):
            return base_url[:-5] + f"/savt_test_{worker_id}"
        elif base_url.endswith("/savt_test"):
            return base_url[:-10] + f"/savt_test_{worker_id}"
        else:
            return f"{base_url}_test_{worker_id}"
    return "sqlite://"  # Default: in-memory SQLite


@pytest.fixture(name="session")
def session_fixture():
    database_url = _get_test_database_url()

    if database_url.startswith("postgresql"):
        # Create the test database first for PostgreSQL
        try:
            from urllib.parse import urlparse

            from sqlalchemy import text

            parsed = urlparse(database_url)
            test_db_name = parsed.path[1:]  # Remove leading slash

            # Connect to default postgres database to create test database
            admin_url = f"postgresql://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}/postgres"
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            with admin_engine.connect() as conn:
                # Check if database exists first
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                    {"dbname": test_db_name},
                )
                if not result.fetchone():
                    conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
            admin_engine.dispose()
        except Exception as e:
            # Log the error but continue - database might already exist
            import sys

            print(
                f"Warning: Could not create test database {test_db_name}: {e}",
                file=sys.stderr,
            )

        # PostgreSQL configuration for integration tests
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    else:
        # SQLite configuration for unit tests
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

    # Clean up PostgreSQL test data if needed
    if database_url.startswith("postgresql"):
        SQLModel.metadata.drop_all(engine)
        engine.dispose()


def _get_async_test_database_url() -> str:
    """Get async database URL for testing based on environment."""
    if os.getenv("TEST_DATABASE") == "postgresql":
        # Use async PostgreSQL with asyncpg
        base_url = os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/savt"
        )
        # Convert to asyncpg and add test suffix
        async_url = base_url.replace("postgresql://", "postgresql+asyncpg://")

        # For parallel tests, use unique database name per worker
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")

        # Replace only the database name at the end of the URL
        if async_url.endswith("/savt"):
            return async_url[:-5] + f"/savt_test_{worker_id}"
        elif async_url.endswith("/savt_test"):
            return async_url[:-10] + f"/savt_test_{worker_id}"
        else:
            return f"{async_url}_test_{worker_id}"
    return "sqlite+aiosqlite:///:memory:"  # Default: in-memory SQLite


@pytest.fixture(name="async_session")
async def async_session_fixture():
    """Async session fixture for testing async database operations."""
    database_url = _get_async_test_database_url()

    if database_url.startswith("postgresql"):
        # PostgreSQL async configuration for integration tests
        async_engine = create_async_engine(
            database_url,
            pool_size=20,
            max_overflow=15,
            pool_recycle=3600,
            pool_pre_ping=True,
        )
    else:
        # SQLite async configuration for unit tests
        async_engine = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSession(async_engine) as session:
        yield session

    # Clean up
    if database_url.startswith("postgresql"):
        async with async_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    await async_engine.dispose()
