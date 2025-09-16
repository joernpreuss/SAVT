# pyright: reportImportCycles=false
from datetime import datetime, timedelta
from typing import Final, NamedTuple

from sqlmodel import Session

from ..infrastructure.database.models import Feature, Item
from ..logging_config import get_logger

logger: Final = get_logger(__name__)


class DeletedItem(NamedTuple):
    """Stores deleted item data for undo."""

    item: Item
    features: list[Feature]
    deleted_at: datetime


class DeletedFeature(NamedTuple):
    """Stores deleted feature data for undo."""

    feature: Feature
    deleted_at: datetime


# In-memory storage for deleted items (expires after 30 seconds)
_deleted_items: dict[str, DeletedItem] = {}
_deleted_features: dict[int, DeletedFeature] = {}

UNDO_TIMEOUT_SECONDS = 30


def _cleanup_expired_deletions() -> None:
    """Remove expired deletions from memory."""
    cutoff = datetime.now() - timedelta(seconds=UNDO_TIMEOUT_SECONDS)

    # Clean up expired items
    expired_items = [
        key for key, item in _deleted_items.items() if item.deleted_at < cutoff
    ]
    for key in expired_items:
        del _deleted_items[key]

    # Clean up expired features
    expired_feature_ids = [
        feature_id
        for feature_id, feature in _deleted_features.items()
        if feature.deleted_at < cutoff
    ]
    for feature_id in expired_feature_ids:
        del _deleted_features[feature_id]


def store_deleted_item(item: Item, features: list[Feature]) -> None:
    """Store deleted item for potential undo."""
    _cleanup_expired_deletions()
    _deleted_items[item.name] = DeletedItem(item, features, datetime.now())
    logger.debug(
        "Stored deleted item for undo",
        item_name=item.name,
        features_count=len(features),
    )


def store_deleted_feature(feature: Feature) -> None:
    """Store deleted feature for potential undo."""
    if feature.id is None:
        logger.warning("Cannot store feature for undo - no ID")
        return

    _cleanup_expired_deletions()
    _deleted_features[feature.id] = DeletedFeature(feature, datetime.now())
    logger.debug(
        "Stored deleted feature for undo",
        feature_id=feature.id,
        feature_name=feature.name,
    )


def undo_item_deletion(session: Session, item_name: str) -> tuple[bool, str]:
    """Restore a deleted item and its features.

    Returns:
        (success, message)
    """
    _cleanup_expired_deletions()

    if item_name not in _deleted_items:
        logger.warning(
            "Cannot undo item deletion - not found or expired", item_name=item_name
        )
        return False, "Cannot undo: deletion too old or item not found"

    deleted_item = _deleted_items[item_name]

    try:
        # Import here to avoid circular imports
        from .feature_service import create_feature as _create_feature
        from .item_service import create_item as _create_item

        # Recreate the item
        restored_item = _create_item(session, deleted_item.item)

        # Recreate the features with the restored item_id
        for feature in deleted_item.features:
            feature.item_id = restored_item.id
            feature.id = None  # Let database assign new ID
            _create_feature(session, feature)

        # Remove from undo storage
        del _deleted_items[item_name]

        logger.info("Item deletion undone successfully", item_name=item_name)
        return True, f"Restored {item_name} with {len(deleted_item.features)} features"

    except Exception as e:
        logger.error("Failed to undo item deletion", item_name=item_name, error=str(e))
        return False, f"Failed to restore {item_name}: {str(e)}"


def undo_feature_deletion(session: Session, feature_id: int) -> tuple[bool, str]:
    """Restore a deleted feature.

    Returns:
        (success, message)
    """
    _cleanup_expired_deletions()

    if feature_id not in _deleted_features:
        logger.warning(
            "Cannot undo feature deletion - not found or expired", feature_id=feature_id
        )
        return False, "Cannot undo: deletion too old or feature not found"

    deleted_feature = _deleted_features[feature_id]

    try:
        # Import here to avoid circular imports
        from .feature_service import create_feature as _create_feature

        # Recreate the feature
        feature = deleted_feature.feature
        feature.id = None  # Let database assign new ID
        _create_feature(session, feature)

        # Remove from undo storage
        del _deleted_features[feature_id]

        logger.info(
            "Feature deletion undone successfully",
            feature_id=feature_id,
            feature_name=feature.name,
        )
        return True, f"Restored {feature.name}"

    except Exception as e:
        logger.error(
            "Failed to undo feature deletion", feature_id=feature_id, error=str(e)
        )
        return False, f"Failed to restore feature: {str(e)}"


def get_undo_info() -> dict[str, int]:
    """Get info about available undos."""
    _cleanup_expired_deletions()
    return {
        "deleted_items": len(_deleted_items),
        "deleted_features": len(_deleted_features),
    }
