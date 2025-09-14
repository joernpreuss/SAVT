from collections.abc import Sequence
from typing import Final

from sqlalchemy.orm import selectinload
from sqlmodel import (
    Session,
    select,
)

from .constants import MAX_NAME_LENGTH
from .logging_config import get_logger
from .logging_utils import log_database_operation, log_user_action
from .models import Feature, Item

logger: Final = get_logger(__name__)


class ItemAlreadyExistsError(ValueError):
    pass


class FeatureAlreadyExistsError(ValueError):
    pass


def _validate_name(name: str, entity_type: str) -> None:
    """Validate entity name (common validation for items and features).

    Args:
        name: The name to validate
        entity_type: Type of entity ('Item' or 'Feature') for error messages

    Raises:
        ValueError: If name is empty or too long
    """
    if not name or not name.strip():
        logger.warning(
            f"{entity_type} creation failed - empty name provided",
            attempted_name=repr(name),
        )
        raise ValueError(f"{entity_type} name cannot be empty")

    if len(name) > MAX_NAME_LENGTH:
        logger.warning(
            f"{entity_type} creation failed - name too long", name_length=len(name)
        )
        raise ValueError(
            f"{entity_type} name cannot be longer than {MAX_NAME_LENGTH} characters"
        )


def _commit_and_refresh(session: Session, entity: Item | Feature) -> Item | Feature:
    """Common pattern for committing and refreshing entities.

    Args:
        session: Database session
        entity: Entity to commit and refresh

    Returns:
        The refreshed entity
    """
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity


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

    # Validate name using common validation function
    _validate_name(item.name, "Item")

    same_name_item: Final = get_item(session, item.name)

    if not same_name_item:
        _commit_and_refresh(session, item)

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


def get_features(session: Session) -> Sequence[Feature]:
    statement: Final = select(Feature)
    results: Final = session.exec(statement)
    features: Final = results.all()
    return features  # type: ignore[no-any-return]


def get_feature(
    session: Session, name: str, item_id: int | None = None
) -> Feature | None:
    statement: Final = select(Feature).where(
        Feature.name == name, Feature.item_id == item_id
    )
    results: Final = session.exec(statement)
    feature: Final = results.first()
    return feature  # type: ignore[no-any-return]


def get_feature_by_id(session: Session, feature_id: int) -> Feature | None:
    statement: Final = select(Feature).where(Feature.id == feature_id)
    results: Final = session.exec(statement)
    feature: Final = results.first()
    return feature  # type: ignore[no-any-return]


def create_feature(session: Session, feature: Feature) -> Feature:
    logger.debug(
        "Creating feature", feature_name=feature.name, created_by=feature.created_by
    )

    # Validate name using common validation function
    _validate_name(feature.name, "Feature")

    # Allow duplicate features - users can veto them separately
    _commit_and_refresh(session, feature)

    log_database_operation(
        operation="create",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature.id,
        created_by=feature.created_by,
    )

    if feature.created_by:
        log_user_action(
            action="create_feature",
            user=feature.created_by,
            feature_name=feature.name,
            feature_id=feature.id,
        )

    logger.info("Feature created successfully", feature_name=feature.name)
    return feature


def veto_item_feature(
    session: Session,
    user: str,
    name: str,
    item_name: str | None = None,
    veto: bool = True,
) -> Feature | None:
    action = "veto" if veto else "unveto"
    logger.debug(
        f"Processing {action} for user={user}, feature={name}, item={item_name}"
    )

    item_id = None
    if item_name:
        item = get_item(session=session, name=item_name)
        logger.debug("Found item for action", action=action, item=item)
        if item:
            item_id = item.id
    else:
        item_id = None

    feature = get_feature(session=session, name=name, item_id=item_id)
    logger.debug("Found feature for action", action=action, feature=feature)

    if feature:
        vetoed_by_set = set(feature.vetoed_by)
        original_vetoed_by = set(feature.vetoed_by)

        if veto:
            vetoed_by_set.add(user)
        else:
            vetoed_by_set.discard(user)

        # Only update if there's a change
        if original_vetoed_by != vetoed_by_set:
            feature.vetoed_by = sorted(vetoed_by_set)

            logger.debug(
                "Updating feature vetoed_by",
                from_vetoed_by=sorted(original_vetoed_by),
                to_vetoed_by=feature.vetoed_by,
            )
            session.commit()
            session.refresh(feature)

            log_database_operation(
                operation="update",
                table="Feature",
                success=True,
                feature_name=feature.name,
                feature_id=feature.id,
                action=action,
            )

            log_user_action(
                action=f"{action}_feature",
                user=user,
                feature_name=feature.name,
                item_name=item_name,
                vetoed_by_count=len(feature.vetoed_by),
            )

            logger.info(
                "Feature action completed successfully",
                action=action,
                user=user,
                feature_name=feature.name,
            )
        else:
            logger.debug(
                "No change needed for action",
                action=action,
                user=user,
                feature_name=feature.name,
            )
    else:
        logger.warning(
            f"Feature not found for {action}",
            extra={"feature_name": name, "item_name": item_name, "user": user},
        )

    return feature


def move_feature(
    session: Session,
    feature_name: str,
    source_item_name: str | None,
    target_item_name: str | None,
) -> Feature | None:
    """Move a feature from one item to another (or to/from standalone).

    Args:
        session: Database session
        feature_name: Name of the feature to move
        source_item_name: Current item name (None for standalone features)
        target_item_name: Target item name (None to make it standalone)

    Returns:
        The moved feature or None if not found
    """
    logger.debug(
        "Moving feature",
        feature_name=feature_name,
        from_item=source_item_name,
        to_item=target_item_name,
    )

    # Get source item ID
    source_item_id = None
    if source_item_name:
        source_item = get_item(session, source_item_name)
        if source_item:
            source_item_id = source_item.id
        else:
            logger.warning("Source item not found", item_name=source_item_name)
            return None

    # Get target item ID
    target_item_id = None
    if target_item_name:
        target_item = get_item(session, target_item_name)
        if target_item:
            target_item_id = target_item.id
        else:
            logger.warning("Target item not found", item_name=target_item_name)
            return None

    # Find the feature to move
    feature = get_feature(session, feature_name, source_item_id)
    if not feature:
        logger.warning(
            "Feature not found for move",
            feature_name=feature_name,
            source_item_name=source_item_name,
        )
        return None

    # Allow duplicate feature names - users can veto them separately

    # Move the feature
    old_item_id = feature.item_id
    feature.item_id = target_item_id

    session.commit()
    session.refresh(feature)

    log_database_operation(
        operation="move",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature.id,
        from_item_id=old_item_id,
        to_item_id=target_item_id,
    )

    logger.info(
        "Feature moved successfully",
        feature_name=feature.name,
        from_item=source_item_name,
        to_item=target_item_name,
    )

    return feature


def veto_feature_by_id(
    session: Session, user: str, feature_id: int, veto: bool = True
) -> Feature | None:
    action = "veto" if veto else "unveto"
    logger.debug(f"Processing {action} for user={user}, feature_id={feature_id}")

    feature = get_feature_by_id(session, feature_id)
    logger.debug("Found feature for action", action=action, feature=feature)

    if feature:
        vetoed_by_set = set(feature.vetoed_by)
        original_vetoed_by = set(feature.vetoed_by)

        if veto:
            vetoed_by_set.add(user)
        else:
            vetoed_by_set.discard(user)

        # Only update if there's a change
        if original_vetoed_by != vetoed_by_set:
            feature.vetoed_by = sorted(vetoed_by_set)

            logger.debug(
                "Updating feature vetoed_by",
                from_vetoed_by=sorted(original_vetoed_by),
                to_vetoed_by=feature.vetoed_by,
            )
            session.commit()
            session.refresh(feature)

            log_database_operation(
                operation="update",
                table="Feature",
                success=True,
                feature_name=feature.name,
                feature_id=feature.id,
                action=action,
            )

            log_user_action(
                action=f"{action}_feature",
                user=user,
                feature_name=feature.name,
                feature_id=feature_id,
                vetoed_by_count=len(feature.vetoed_by),
            )

            logger.info(
                "Feature action completed successfully",
                action=action,
                user=user,
                feature_name=feature.name,
            )
        else:
            logger.debug(
                "No change needed for action",
                action=action,
                user=user,
                feature_name=feature.name,
            )
    else:
        logger.warning(
            f"Feature not found for {action}",
            extra={"feature_id": feature_id, "user": user},
        )

    return feature
