from collections.abc import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.future import Engine
from sqlmodel import Session, SQLModel, create_engine

from ...config import settings

# from sqlmodel.pool import StaticPool


def _get_engine() -> Engine:
    # Use effective_database_url which handles both DATABASE_URL and DB_NAME
    database_url = settings.effective_database_url
    connect_args: dict[str, bool] = {}
    engine_kwargs: dict[str, int | bool] = {}

    # Configure connection args based on database type
    if "sqlite" in database_url:
        # SQLite specific configurations
        if settings.debug:
            connect_args["check_same_thread"] = False
    elif "postgresql" in database_url:
        # PostgreSQL specific configurations
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_size"] = 10
        engine_kwargs["max_overflow"] = 20

    engine = create_engine(
        database_url,
        # echo=True,  # Enable for SQL debugging
        connect_args=connect_args,
        **engine_kwargs,
        # poolclass=StaticPool,  # Only use for testing
    )
    return engine


def _get_async_engine() -> AsyncEngine:
    """Create async engine with optimized connection pooling for concurrent users."""
    database_url = settings.effective_database_url

    # Convert sync URL to async URL and set engine kwargs
    engine_kwargs: dict[str, int | bool]

    if "sqlite" in database_url:
        # For SQLite, use aiosqlite
        async_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        engine_kwargs = {
            "echo": settings.debug,
        }
    elif "postgresql" in database_url:
        # For PostgreSQL, use asyncpg
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        engine_kwargs = {
            "echo": settings.debug,
            "pool_size": 20,  # Core pool size for 33 users
            "max_overflow": 15,  # Additional connections during peaks
            "pool_recycle": 3600,  # Recycle connections every hour
            "pool_pre_ping": True,  # Validate connections before use
        }
    else:
        raise ValueError(f"Unsupported database URL: {database_url}")

    return create_async_engine(async_url, **engine_kwargs)


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)


_engine: Engine | None = None
_async_engine: AsyncEngine | None = None


def get_main_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def get_async_engine() -> AsyncEngine:
    """Get the async database engine with connection pooling."""
    global _async_engine
    if _async_engine is None:
        _async_engine = _get_async_engine()
    return _async_engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_main_engine()) as session:
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session with proper transaction management."""
    async with AsyncSession(get_async_engine()) as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_async_db(engine: AsyncEngine) -> None:
    """Initialize database tables using async engine."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
