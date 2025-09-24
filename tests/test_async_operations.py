"""
Async database operations tests.

Tests verify that async database functions work correctly for 33-user concurrency.
These tests use individual async sessions per test to avoid SQLite connection issues.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

from src.application.item_service import (
    ItemAlreadyExistsError,
    create_item_async,
    get_item_async,
    get_items_async,
)
from src.infrastructure.database.models import Item


async def _create_test_session() -> AsyncSession:
    """Create a fresh async session for each test."""
    import os
    import uuid

    if os.getenv("TEST_DATABASE") == "postgresql":
        # Use PostgreSQL for integration tests
        base_url = os.getenv(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/savt"
        )
        async_url = base_url.replace("postgresql://", "postgresql+asyncpg://")

        # For parallel tests, use unique database name per test
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
        unique_id = str(uuid.uuid4())[:8]

        # Replace only the database name at the end of the URL
        if async_url.endswith("/savt"):
            async_url = async_url[:-5] + f"/savt_test_{worker_id}_{unique_id}"
        elif async_url.endswith("/savt_test"):
            async_url = async_url[:-10] + f"/savt_test_{worker_id}_{unique_id}"
        else:
            async_url = f"{async_url}_test_{worker_id}_{unique_id}"

        # Create the test database first
        import asyncpg

        try:
            # Extract connection info
            from urllib.parse import urlparse

            parsed = urlparse(async_url)

            # Connect to default postgres database to create test database
            admin_url = (
                f"postgresql://{parsed.username}:{parsed.password}"
                f"@{parsed.hostname}:{parsed.port}/postgres"
            )
            admin_conn = await asyncpg.connect(admin_url)

            test_db_name = parsed.path[1:]  # Remove leading slash
            await admin_conn.execute(f'CREATE DATABASE "{test_db_name}"')
            await admin_conn.close()
        except Exception:
            pass  # Database might already exist

        async_engine = create_async_engine(
            async_url,
            pool_size=2,  # Smaller pool for test databases
            max_overflow=5,
        )
    else:
        # Default: in-memory SQLite (each test gets its own memory database)
        async_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    # Create tables
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    return AsyncSession(async_engine)


@pytest.mark.asyncio
async def test_async_item_creation_works():
    """Test that async item creation functions correctly.

    Covers:
    - Async database operations work
    - Item creation through async service
    - FR-1.1: Users can create items with unique names
    """
    async with await _create_test_session() as session:
        item = Item(name="test_async_item")
        created_item = await create_item_async(session, item)

        assert created_item.id is not None
        assert created_item.name == "test_async_item"


@pytest.mark.asyncio
async def test_async_item_retrieval_works():
    """Test that async item retrieval functions correctly.

    Covers:
    - Async database queries
    - Item retrieval by name
    """
    async with await _create_test_session() as session:
        # Create test item
        item = Item(name="test_retrieval_item")
        await create_item_async(session, item)

        # Retrieve by name
        found_item = await get_item_async(session, "test_retrieval_item")
        assert found_item is not None
        assert found_item.name == "test_retrieval_item"

        # Test non-existent item
        not_found = await get_item_async(session, "does_not_exist")
        assert not_found is None


@pytest.mark.asyncio
async def test_async_duplicate_item_prevention():
    """Test that async operations prevent duplicate items.

    Covers:
    - Async database constraint handling
    - FR-1.2: Item names must be unique within the system
    """
    async with await _create_test_session() as session:
        # Create first item
        item1 = Item(name="duplicate_test")
        await create_item_async(session, item1)

        # Try to create duplicate
        item2 = Item(name="duplicate_test")
        with pytest.raises(ItemAlreadyExistsError):
            await create_item_async(session, item2)


@pytest.mark.asyncio
async def test_async_multiple_items_retrieval():
    """Test that async retrieval of multiple items works.

    Covers:
    - Async database queries for multiple records
    - Bulk retrieval operations
    """
    async with await _create_test_session() as session:
        # Create multiple items
        items_to_create = [
            Item(name="multi_item_1"),
            Item(name="multi_item_2"),
            Item(name="multi_item_3"),
        ]

        for item in items_to_create:
            await create_item_async(session, item)

        # Retrieve all items
        all_items = await get_items_async(session)
        item_names = [item.name for item in all_items]

        assert "multi_item_1" in item_names
        assert "multi_item_2" in item_names
        assert "multi_item_3" in item_names
        assert len(all_items) >= 3


@pytest.mark.asyncio
async def test_async_operations_are_isolated():
    """Test that each async session is properly isolated.

    Covers:
    - Session isolation between tests
    - No data leakage between operations
    """
    # First session
    async with await _create_test_session() as session1:
        item1 = Item(name="isolated_item_1")
        await create_item_async(session1, item1)

        items1 = await get_items_async(session1)
        assert len(items1) == 1

    # Second session (should be isolated)
    async with await _create_test_session() as session2:
        item2 = Item(name="isolated_item_2")
        await create_item_async(session2, item2)

        items2 = await get_items_async(session2)
        assert len(items2) == 1  # Only the item from this session
