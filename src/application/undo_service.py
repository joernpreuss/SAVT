"""Persistent database-backed undo service.

Provides undo functionality for deleted items and features using database storage
instead of in-memory dictionaries, ensuring data survives server restarts.
"""

import json
from datetime import datetime, timedelta

from sqlmodel import Session, select

from ..infrastructure.database.models import Feature, Item
from ..infrastructure.database.undo_models import (
    DeletedFeatureRecord,
    DeletedItemRecord,
)
from ..logging_config import get_logger

logger = get_logger(__name__)

_UNDO_TIMEOUT_SECONDS = 30


def _cleanup_expired_deletions(session: Session) -> None:
    """Remove expired deletions from database."""
    cutoff = datetime.now()

    # Clean up expired items
    expired_items = session.exec(
        select(DeletedItemRecord).where(DeletedItemRecord.expires_at < cutoff)
    ).all()
    for item in expired_items:
        session.delete(item)

    # Clean up expired features
    expired_features = session.exec(
        select(DeletedFeatureRecord).where(DeletedFeatureRecord.expires_at < cutoff)
    ).all()
    for feature in expired_features:
        session.delete(feature)

    if expired_items or expired_features:
        session.commit()
        logger.debug(
            "Cleaned up expired undo records",
            items_removed=len(expired_items),
            features_removed=len(expired_features),
        )


def store_deleted_item(session: Session, item: Item, features: list[Feature]) -> None:
    """Store deleted item and features for potential undo."""
    _cleanup_expired_deletions(session)

    # Serialize features data
    features_data = json.dumps(
        [
            {
                "id": f.id,
                "name": f.name,
                "kind": f.kind,
                "item_id": f.item_id,
                "vetoed_by": f.vetoed_by,
            }
            for f in features
        ]
    )

    deleted_record = DeletedItemRecord(
        original_name=item.name,
        original_kind=item.kind,
        deleted_at=datetime.now(),
        features_data=features_data,
        expires_at=datetime.now() + timedelta(seconds=_UNDO_TIMEOUT_SECONDS),
    )

    session.add(deleted_record)
    session.commit()

    logger.debug(
        "Stored deleted item for undo in database",
        item_name=item.name,
        features_count=len(features),
        expires_at=deleted_record.expires_at,
    )


def store_deleted_feature(session: Session, feature: Feature) -> None:
    """Store deleted feature for potential undo."""
    if feature.id is None:
        logger.warning("Cannot store feature for undo - no ID")
        return

    _cleanup_expired_deletions(session)

    deleted_record = DeletedFeatureRecord(
        original_feature_id=feature.id,
        original_name=feature.name,
        original_kind=feature.kind,
        original_item_id=feature.item_id,
        original_vetoed_by=json.dumps(feature.vetoed_by),
        deleted_at=datetime.now(),
        expires_at=datetime.now() + timedelta(seconds=_UNDO_TIMEOUT_SECONDS),
    )

    session.add(deleted_record)
    session.commit()

    logger.debug(
        "Stored deleted feature for undo in database",
        feature_id=feature.id,
        feature_name=feature.name,
        expires_at=deleted_record.expires_at,
    )


def undo_item_deletion(session: Session, item_name: str) -> tuple[bool, str]:
    """Restore a deleted item and its features from database storage.

    Returns:
        (success, message)
    """
    _cleanup_expired_deletions(session)

    # Find the deleted item record
    deleted_record = session.exec(
        select(DeletedItemRecord).where(DeletedItemRecord.original_name == item_name)
    ).first()

    if not deleted_record:
        logger.warning(
            "Cannot undo item deletion - not found or expired", item_name=item_name
        )
        return False, "Cannot undo: deletion too old or item not found"

    try:
        # Import here to avoid circular imports
        from .feature_service import create_feature as _create_feature
        from .item_service import create_item as _create_item

        # Recreate the item
        restored_item_data = Item(
            name=deleted_record.original_name, kind=deleted_record.original_kind
        )
        restored_item = _create_item(session, restored_item_data)

        # Deserialize and recreate features
        features_data = json.loads(deleted_record.features_data)
        restored_features_count = 0

        for feature_data in features_data:
            feature = Feature(
                name=feature_data["name"],
                kind=feature_data["kind"],
                item_id=restored_item.id,
                vetoed_by=feature_data["vetoed_by"],
            )
            _create_feature(session, feature)
            restored_features_count += 1

        # Remove the undo record
        session.delete(deleted_record)
        session.commit()

        logger.info(
            "Item deletion undone successfully from database",
            item_name=item_name,
            features_restored=restored_features_count,
        )
        return True, f"Restored {item_name} with {restored_features_count} features"

    except Exception as e:
        session.rollback()
        logger.error("Failed to undo item deletion", item_name=item_name, error=str(e))
        return False, f"Failed to restore {item_name}: {str(e)}"


def undo_feature_deletion(session: Session, feature_id: int) -> tuple[bool, str]:
    """Restore a deleted feature from database storage.

    Returns:
        (success, message)
    """
    _cleanup_expired_deletions(session)

    # Find the deleted feature record
    deleted_record = session.exec(
        select(DeletedFeatureRecord).where(
            DeletedFeatureRecord.original_feature_id == feature_id
        )
    ).first()

    if not deleted_record:
        logger.warning(
            "Cannot undo feature deletion - not found or expired", feature_id=feature_id
        )
        return False, "Cannot undo: deletion too old or feature not found"

    try:
        # Import here to avoid circular imports
        from .feature_service import create_feature as _create_feature

        # Recreate the feature
        feature = Feature(
            name=deleted_record.original_name,
            kind=deleted_record.original_kind,
            item_id=deleted_record.original_item_id,
            vetoed_by=json.loads(deleted_record.original_vetoed_by),
        )
        _create_feature(session, feature)

        # Remove the undo record
        session.delete(deleted_record)
        session.commit()

        logger.info(
            "Feature deletion undone successfully from database",
            original_feature_id=feature_id,
            feature_name=deleted_record.original_name,
        )
        return True, f"Restored {deleted_record.original_name}"

    except Exception as e:
        session.rollback()
        logger.error(
            "Failed to undo feature deletion", feature_id=feature_id, error=str(e)
        )
        return False, f"Failed to restore feature: {str(e)}"


def get_undo_info(session: Session) -> dict[str, int]:
    """Get info about available undos from database."""
    _cleanup_expired_deletions(session)

    items_count = len(session.exec(select(DeletedItemRecord)).all())
    features_count = len(session.exec(select(DeletedFeatureRecord)).all())

    return {
        "deleted_items": items_count,
        "deleted_features": features_count,
    }
