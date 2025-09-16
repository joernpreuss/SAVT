from typing import Final

from sqlmodel import Session

from ..domain.constants import MAX_FEATURE_AMOUNT, MAX_NAME_LENGTH
from ..infrastructure.database.models import Feature, Item
from ..logging_config import get_logger
from ..logging_utils import log_database_operation
from ..utils import smart_shorten_name
from .feature_service import get_feature
from .item_service import create_item, get_item

logger: Final = get_logger(__name__)


def move_feature(
    session: Session,
    feature_name: str,
    source_item_name: str | None,
    target_item_name: str | None,
) -> tuple[Feature | None, str | None]:
    """Move a feature from one item to another (or to/from standalone).

    This function moves a feature and combines it with existing features of the
    same name at the target location. If the combination would exceed the maximum
    amount, only the amount that fits is moved, and the excess stays at the source.

    Args:
        session: Database session
        feature_name: Name of the feature to move
        source_item_name: Current item name (None for standalone features)
        target_item_name: Target item name (None to make it standalone)

    Returns:
        Tuple of (moved/combined feature or None, user message or None)
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
            return None, f"Source item '{source_item_name}' not found"

    # Get target item ID
    target_item_id = None
    if target_item_name:
        target_item = get_item(session, target_item_name)
        if target_item:
            target_item_id = target_item.id
        else:
            logger.warning("Target item not found", item_name=target_item_name)
            return None, f"Target item '{target_item_name}' not found"

    # Find the feature to move
    source_feature = get_feature(session, feature_name, source_item_id)
    if not source_feature:
        logger.warning(
            "Feature not found for move",
            feature_name=feature_name,
            source_item_name=source_item_name,
        )
        return None, f"Feature '{feature_name}' not found"

    # Check if target already has this feature
    target_feature = get_feature(session, feature_name, target_item_id)

    if target_feature:
        # Calculate how much can be moved without exceeding the maximum
        available_space = MAX_FEATURE_AMOUNT - target_feature.amount
        amount_to_move = min(source_feature.amount, available_space)

        if amount_to_move > 0:
            # Move the calculated amount
            target_feature.amount += amount_to_move
            source_feature.amount -= amount_to_move

            # If source feature has no amount left, delete it
            if source_feature.amount == 0:
                session.delete(source_feature)
            else:
                session.add(source_feature)

            session.add(target_feature)
            session.commit()
            session.refresh(target_feature)

            logger.info(
                "Feature partially moved",
                feature_name=feature_name,
                amount_moved=amount_to_move,
                remaining_at_source=(
                    source_feature.amount if source_feature.amount > 0 else 0
                ),
                target_total=target_feature.amount,
            )

            log_database_operation(
                operation="move_partial",
                table="Feature",
                success=True,
                feature_name=feature_name,
                feature_id=target_feature.id,
                from_item_id=source_item_id,
                to_item_id=target_item_id,
                amount_moved=amount_to_move,
            )

            remaining = source_feature.amount if source_feature.amount > 0 else 0
            if remaining > 0:
                target_display = target_item_name or "Free"
                source_display = source_item_name or "Free"
                message = (
                    f"{feature_name} partially moved to {target_display} - "
                    f"{remaining}x remains at {source_display}"
                )
            else:
                target_display = target_item_name or "Free"
                message = f"{feature_name} moved completely to {target_display}"
            return target_feature, message
        else:
            # Target is already at maximum, nothing can be moved
            logger.info(
                "Feature already at maximum - no move possible",
                feature_name=feature_name,
                target_amount=target_feature.amount,
            )
            target_display = target_item_name or "Free"
            message = (
                f"{feature_name} at {target_display} is already at maximum "
                f"({MAX_FEATURE_AMOUNT}x) - nothing moved"
            )
            return target_feature, message
    else:
        # No existing feature at target - move entire feature
        old_item_id = source_feature.item_id
        source_feature.item_id = target_item_id
        session.add(source_feature)
        session.commit()
        session.refresh(source_feature)

        log_database_operation(
            operation="move_full",
            table="Feature",
            success=True,
            feature_name=feature_name,
            feature_id=source_feature.id,
            from_item_id=old_item_id,
            to_item_id=target_item_id,
        )

        logger.info(
            "Feature moved completely",
            feature_name=feature_name,
            from_item=source_item_name,
            to_item=target_item_name,
            amount=source_feature.amount,
        )

        target_display = target_item_name or "Free"
        message = f"{feature_name} ({source_feature.amount}x) moved to {target_display}"
        return source_feature, message


def merge_items(
    session: Session,
    source_item_name: str,
    target_item_name: str,
) -> tuple[Item | None, str | None]:
    """Merge all features from source item into target item, then delete source.

    Args:
        session: Database session
        source_item_name: Name of item to merge from (will be deleted)
        target_item_name: Name of item to merge into (will remain)

    Returns:
        Tuple of (target item or None, user message or None)
    """
    logger.debug(
        "Merging items",
        source_item=source_item_name,
        target_item=target_item_name,
    )

    # Get both items
    source_item = get_item(session, source_item_name)
    if not source_item:
        return None, f"Source item '{source_item_name}' not found"

    target_item = get_item(session, target_item_name)
    if not target_item:
        return None, f"Target item '{target_item_name}' not found"

    if source_item.id == target_item.id:
        return None, "Cannot merge an item with itself"

    # Get all features from source item
    source_features = list(source_item.features)

    if not source_features:
        # No features to merge, just delete the empty source item
        session.delete(source_item)
        session.commit()
        return (
            target_item,
            f"Empty item '{source_item_name}' merged into '{target_item_name}'",
        )

    moved_features = []
    partial_moves = []

    # Move each feature from source to target
    for feature in source_features:
        result, message = move_feature(
            session, feature.name, source_item_name, target_item_name
        )
        if result:
            moved_features.append(feature.name)
            if "partially moved" in (message or ""):
                partial_moves.append(feature.name)

    # Create new concatenated name with smart shortening handling
    base_name = f"{source_item_name}-{target_item_name}"
    base_name = smart_shorten_name(base_name)

    new_item_name = base_name
    counter = 2
    while get_item(session, new_item_name) is not None:
        # For numbered versions, we need to account for the number suffix
        suffix = f"-{counter}"
        max_base_length = MAX_NAME_LENGTH - len(suffix)
        truncated_base = smart_shorten_name(base_name, max_base_length)
        new_item_name = f"{truncated_base}{suffix}"
        counter += 1

    # Update target item name
    target_item.name = new_item_name
    session.add(target_item)

    # Delete the source item (should be empty now or have only partial remainders)
    session.refresh(source_item)  # Refresh to see current state
    remaining_features = list(source_item.features)

    if not remaining_features:
        session.delete(source_item)
        session.commit()

        if partial_moves:
            moved_count = len(moved_features)
            partial_count = len(partial_moves)
            message = (
                f"'{source_item_name}' merged into '{new_item_name}' "
                f"({moved_count} features moved, {partial_count} partial)"
            )
        else:
            message = f"'{source_item_name}' merged completely into '{new_item_name}'"
    else:
        # Some features remained due to capacity limits
        remaining_names = [f.name for f in remaining_features]
        message = (
            f"'{source_item_name}' partially merged into '{new_item_name}' - "
            f"{', '.join(remaining_names)} remain"
        )

    log_database_operation(
        operation="merge_items",
        table="Item",
        success=True,
        source_item_name=source_item_name,
        target_item_name=new_item_name,
        features_moved=len(moved_features),
    )

    logger.info(
        "Items merged successfully",
        source_item=source_item_name,
        target_item=new_item_name,
        features_moved=len(moved_features),
    )

    return target_item, message


def split_item(
    session: Session,
    source_item_name: str,
) -> tuple[list[Item], str | None]:
    """Split an item into separate items, one for each unique feature.

    Args:
        session: Database session
        source_item_name: Name of item to split

    Returns:
        Tuple of (list of new items, user message or None)
    """
    logger.debug("Splitting item", source_item=source_item_name)

    # Get source item
    source_item = get_item(session, source_item_name)
    if not source_item:
        return [], f"Item '{source_item_name}' not found"

    # Get all features grouped by name
    features = source_item.features
    if len(features) == 0:
        return [], f"Item '{source_item_name}' has no features to split"

    # Group features by name (combine amounts)
    feature_groups: dict[str, int] = {}
    for feature in features:
        if feature.name in feature_groups:
            feature_groups[feature.name] += feature.amount
        else:
            feature_groups[feature.name] = feature.amount

    if len(feature_groups) <= 1:
        # Special case: single feature with amount > 1
        if len(feature_groups) == 1:
            feature_name, total_amount = next(iter(feature_groups.items()))
            if total_amount > 1:
                # Split into individual items with amount 1 each
                created_items = []
                for i in range(1, total_amount + 1):
                    # Generate unique name with numbering
                    base_name = f"{source_item_name}-{i}"
                    base_name = smart_shorten_name(base_name)

                    new_item_name = base_name
                    counter = 2

                    # Check if name already exists and add number if needed
                    while get_item(session, new_item_name) is not None:
                        suffix = f"-{counter}"
                        max_base_length = MAX_NAME_LENGTH - len(suffix)
                        truncated_base = smart_shorten_name(base_name, max_base_length)
                        new_item_name = f"{truncated_base}{suffix}"
                        counter += 1

                    new_item = create_item(
                        session, Item(name=new_item_name, kind=source_item.kind)
                    )

                    # Add the feature with amount 1
                    new_feature = Feature(
                        name=feature_name,
                        amount=1,
                        item_id=new_item.id,
                        created_by=source_item.created_by,
                    )
                    session.add(new_feature)
                    created_items.append(new_item)

                # Delete the original item
                session.delete(source_item)
                session.commit()

                message = (
                    f"Split '{source_item_name}' into {total_amount} individual items"
                )
                return created_items, message

        return (
            [],
            f"Item '{source_item_name}' has only one unique feature with amount 1 - "
            + "cannot split",
        )

    created_items = []

    # Create new item for each unique feature
    for feature_name, total_amount in feature_groups.items():
        # Generate unique name with duplicate prevention and smart shortening
        base_name = f"{source_item_name}-{feature_name}"
        base_name = smart_shorten_name(base_name)

        new_item_name = base_name
        counter = 2

        # Check if name already exists and add number if needed
        while get_item(session, new_item_name) is not None:
            # For numbered versions, account for the number suffix
            suffix = f"-{counter}"
            max_base_length = MAX_NAME_LENGTH - len(suffix)
            truncated_base = smart_shorten_name(base_name, max_base_length)
            new_item_name = f"{truncated_base}{suffix}"
            counter += 1

        new_item = create_item(session, Item(name=new_item_name, kind=source_item.kind))

        # Add the feature to the new item
        new_feature = Feature(
            name=feature_name,
            amount=min(total_amount, MAX_FEATURE_AMOUNT),
            item_id=new_item.id,
            created_by=None,  # Could inherit from original features
        )

        # Import create_feature locally to avoid circular import
        from .feature_service import create_feature

        create_feature(session, new_feature)
        created_items.append(new_item)

    # Delete the original item
    session.delete(source_item)
    session.commit()

    item_names = [item.name for item in created_items]
    message = (
        f"'{source_item_name}' split into {len(created_items)} items: "
        f"{', '.join(item_names)}"
    )

    log_database_operation(
        operation="split_item",
        table="Item",
        success=True,
        source_item_name=source_item_name,
        new_items_count=len(created_items),
    )

    logger.info(
        "Item split successfully",
        source_item=source_item_name,
        new_items_count=len(created_items),
    )

    return created_items, message
