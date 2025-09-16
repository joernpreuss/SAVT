from collections.abc import Sequence
from typing import Final

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ..domain.constants import MAX_NAME_LENGTH
from ..infrastructure.database.models import Item
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
