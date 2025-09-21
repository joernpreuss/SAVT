from collections.abc import Sequence
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..infrastructure.database.models import Item
from ..logging_config import get_logger
from ..logging_utils import log_database_operation
from .validation import validate_entity_name_with_logging

logger: Final = get_logger(__name__)


class ItemAlreadyExistsError(ValueError):
    pass


def _validate_item_name(name: str) -> None:
    """Validate item name using shared validation logic.

    Args:
        name: The name to validate

    Raises:
        ValueError: If name is empty, too long, or contains problematic characters
    """
    validate_entity_name_with_logging(name, "item")


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
    statement: Final = (
        select(Item)
        .where(Item.deleted_at.is_(None))  # type: ignore[union-attr]
        .options(selectinload(Item.features))
    )
    results: Final = session.exec(statement)
    items: Final = results.all()

    # Filter out deleted features from the loaded items
    for item in items:
        item.features = [f for f in item.features if f.deleted_at is None]

    return items  # type: ignore[no-any-return]


def get_item(session: Session, name: str) -> Item | None:
    statement: Final = select(Item).where(Item.name == name, Item.deleted_at.is_(None))  # type: ignore[union-attr]
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
    """Soft delete an item and move its features to standalone.

    Args:
        session: Database session
        item_name: Name of the item to delete

    Returns:
        True if item was deleted, False if not found
    """
    logger.debug("Soft deleting item", item_name=item_name)

    item: Final = get_item(session, item_name)
    if not item:
        logger.warning("Item deletion failed - not found", item_name=item_name)
        return False

    # Convert to domain entity and perform soft delete
    domain_item = item.to_domain()
    domain_item.soft_delete()

    # Update the database model
    item.deleted_at = domain_item.deleted_at

    # Move all features to standalone (set item_id to None)
    for feature in item.features:
        feature.item_id = None
        session.add(feature)

    session.add(item)
    session.commit()

    log_database_operation(
        operation="soft_delete",
        table="Item",
        success=True,
        item_name=item_name,
        item_id=item.id,
    )
    logger.info("Item soft deleted successfully", item_name=item_name, item_id=item.id)
    return True


def restore_item(session: Session, item_name: str) -> bool:
    """Restore a soft deleted item.

    Args:
        session: Database session
        item_name: Name of the item to restore

    Returns:
        True if item was restored, False if not found
    """
    logger.debug("Restoring item", item_name=item_name)

    # Look for soft deleted item
    statement: Final = select(Item).where(
        Item.name == item_name,
        Item.deleted_at.is_not(None),  # type: ignore[union-attr]
    )
    results: Final = session.exec(statement)
    item: Final = results.first()

    if not item:
        logger.warning("Item restore failed - not found", item_name=item_name)
        return False

    # Convert to domain entity and restore
    domain_item = item.to_domain()
    domain_item.restore()

    # Update the database model
    item.deleted_at = None

    session.add(item)
    session.commit()

    log_database_operation(
        operation="restore",
        table="Item",
        success=True,
        item_name=item_name,
        item_id=item.id,
    )
    logger.info("Item restored successfully", item_name=item_name, item_id=item.id)
    return True


# Async versions for concurrent database operations


async def get_items_async(session: AsyncSession) -> Sequence[Item]:
    """Get all items with their features using async database operations."""
    statement: Final = (
        select(Item)
        .where(Item.deleted_at.is_(None))  # type: ignore[union-attr]
        .options(selectinload(Item.features))
    )
    result = await session.execute(statement)
    items = result.scalars().all()

    # Filter out deleted features from the loaded items
    for item in items:
        item.features = [f for f in item.features if f.deleted_at is None]

    return items  # type: ignore[no-any-return]


async def get_item_async(session: AsyncSession, name: str) -> Item | None:
    """Get item by name using async database operations."""
    statement: Final = select(Item).where(Item.name == name, Item.deleted_at.is_(None))  # type: ignore[union-attr]
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
    """Soft delete an item and move its features to standalone using async ops."""
    logger.debug("Soft deleting item async", item_name=item_name)

    item: Final = await get_item_async(session, item_name)
    if not item:
        logger.warning("Item deletion failed - not found", item_name=item_name)
        return False

    # Convert to domain entity and perform soft delete
    domain_item = item.to_domain()
    domain_item.soft_delete()

    # Update the database model
    item.deleted_at = domain_item.deleted_at

    # Move all features to standalone (set item_id to None)
    for feature in item.features:
        feature.item_id = None
        session.add(feature)

    session.add(item)
    await session.commit()
    log_database_operation(
        operation="soft_delete",
        table="Item",
        success=True,
        item_name=item_name,
        item_id=item.id,
    )
    logger.info(
        "Item soft deleted successfully async", item_name=item_name, item_id=item.id
    )
    return True
