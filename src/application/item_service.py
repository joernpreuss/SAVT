# pyright: reportImportCycles=false
from collections.abc import Sequence
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..domain.constants import MAX_NAME_LENGTH
from ..infrastructure.database.models import Feature, Item
from ..logging_config import get_logger
from ..logging_utils import log_database_operation

logger: Final = get_logger(__name__)


class ItemAlreadyExistsError(ValueError):
    pass


def _validate_item_name(name: str) -> None:
    """Validate item name.

    Args:
        name: The name to validate

    Raises:
        ValueError: If name is empty or too long
    """
    if not name or not name.strip():
        logger.warning(
            "Item creation failed - empty name provided",
            attempted_name=repr(name),
        )
        raise ValueError("Item name cannot be empty")

    if len(name) > MAX_NAME_LENGTH:
        logger.warning("Item creation failed - name too long", name_length=len(name))
        raise ValueError(
            f"Item name cannot be longer than {MAX_NAME_LENGTH} characters"
        )


def _commit_and_refresh_item(session: Session, item: Item) -> Item:
    """Common pattern for committing and refreshing items.

    Args:
        session: Database session
        item: Item to commit and refresh

    Returns:
        The refreshed item
    """
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def get_items(session: Session) -> Sequence[Item]:
    statement: Final = select(Item).options(selectinload(Item.features))
    results: Final = session.exec(statement)
    items: Final = results.all()
    return items  # type: ignore[no-any-return]


def get_item(session: Session, name: str) -> Item | None:
    statement: Final = select(Item).where(Item.name == name)
    results: Final = session.exec(statement)
    item: Final = results.first()
    return item  # type: ignore[no-any-return]


def create_item(session: Session, item: Item) -> Item:
    logger.debug("Creating item", item_name=item.name)

    # Validate name using item-specific validation function
    _validate_item_name(item.name)

    same_name_item: Final = get_item(session, item.name)

    if not same_name_item:
        _commit_and_refresh_item(session, item)

        log_database_operation(
            operation="create",
            table="Item",
            success=True,
            item_name=item.name,
            item_id=item.id,
        )
        logger.info("Item created successfully", item_name=item.name, item_id=item.id)
        return item
    else:
        logger.warning("Item creation failed - already exists", item_name=item.name)
        raise ItemAlreadyExistsError(f"Item with name '{item.name}' already exists")


def delete_item(session: Session, item_name: str) -> bool:
    """Delete an item and move its features to standalone.

    Args:
        session: Database session
        item_name: Name of the item to delete

    Returns:
        True if item was deleted, False if not found
    """
    logger.debug("Deleting item", item_name=item_name)

    item: Final = get_item(session, item_name)
    if not item:
        logger.warning("Item deletion failed - not found", item_name=item_name)
        return False

    # Store for undo before deletion
    features_copy = [
        Feature(
            name=f.name,
            amount=f.amount,
            created_by=f.created_by,
            vetoed_by=f.vetoed_by.copy(),
            item_id=f.item_id,
        )
        for f in item.features
    ]

    item_copy = Item(name=item.name, kind=item.kind, created_by=item.created_by)

    # Import here to avoid circular imports
    from .undo_service import store_deleted_item

    store_deleted_item(item_copy, features_copy)

    # Move all features to standalone (set item_id to None)
    for feature in item.features:
        feature.item_id = None
        session.add(feature)

    # Delete the item
    session.delete(item)
    session.commit()

    log_database_operation(
        operation="delete",
        table="Item",
        success=True,
        item_name=item_name,
        item_id=item.id,
    )
    logger.info("Item deleted successfully", item_name=item_name, item_id=item.id)
    return True


# Async versions for concurrent database operations


async def get_items_async(session: AsyncSession) -> Sequence[Item]:
    """Get all items with their features using async database operations."""
    statement: Final = select(Item).options(selectinload(Item.features))
    result = await session.execute(statement)
    items = result.scalars().all()
    return items  # type: ignore[no-any-return]


async def get_item_async(session: AsyncSession, name: str) -> Item | None:
    """Get item by name using async database operations."""
    statement: Final = select(Item).where(Item.name == name)
    result = await session.execute(statement)
    item = result.scalars().first()
    return item  # type: ignore[no-any-return]


async def create_item_async(session: AsyncSession, item: Item) -> Item:
    """Create item using async database operations for better concurrency."""
    logger.debug("Creating item async", item_name=item.name)

    # Validate name using item-specific validation function
    _validate_item_name(item.name)

    same_name_item: Final = await get_item_async(session, item.name)

    if not same_name_item:
        session.add(item)
        await session.commit()
        await session.refresh(item)

        log_database_operation(
            operation="create",
            table="Item",
            success=True,
            item_name=item.name,
            item_id=item.id,
        )
        logger.info(
            "Item created successfully async", item_name=item.name, item_id=item.id
        )
        return item
    else:
        logger.warning("Item creation failed - already exists", item_name=item.name)
        raise ItemAlreadyExistsError(f"Item with name '{item.name}' already exists")


async def delete_item_async(session: AsyncSession, item_name: str) -> bool:
    """Delete an item and move its features to standalone using async operations."""
    logger.debug("Deleting item async", item_name=item_name)

    item: Final = await get_item_async(session, item_name)
    if not item:
        logger.warning("Item deletion failed - not found", item_name=item_name)
        return False

    # Store for undo before deletion
    features_copy = [
        Feature(
            name=f.name,
            amount=f.amount,
            created_by=f.created_by,
            vetoed_by=f.vetoed_by.copy(),
            item_id=f.item_id,
        )
        for f in item.features
    ]

    item_copy = Item(name=item.name, kind=item.kind, created_by=item.created_by)

    # Import here to avoid circular imports
    from .undo_service import store_deleted_item

    store_deleted_item(item_copy, features_copy)

    # Move all features to standalone (set item_id to None)
    for feature in item.features:
        feature.item_id = None
        session.add(feature)

    # Delete the item
    # Note: session.delete() is synchronous in SQLAlchemy, not a coroutine
    session.delete(item)  # type: ignore[misc]
    await session.commit()
    log_database_operation(
        operation="delete",
        table="Item",
        success=True,
        item_name=item_name,
        item_id=item.id,
    )
    logger.info("Item deleted successfully async", item_name=item_name, item_id=item.id)
    return True
