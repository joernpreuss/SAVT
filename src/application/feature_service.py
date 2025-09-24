from collections.abc import Sequence
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from ..domain.constants import MAX_FEATURE_AMOUNT
from ..infrastructure.database.models import Feature
from ..logging_config import get_logger
from ..logging_utils import log_database_operation, log_user_action
from ..utils import apply_veto_to_feature
from .validation import commit_and_refresh_entity, validate_entity_name_with_logging

logger: Final = get_logger(__name__)


class FeatureAlreadyExistsError(ValueError):
    pass


def get_features(session: Session) -> Sequence[Feature]:
    statement: Final = select(Feature).where(
        Feature.deleted_at.is_(None)  # type: ignore[union-attr,attr-defined]
    )
    results: Final = session.exec(statement)
    features: Final = results.all()
    return features  # type: ignore[no-any-return]


async def get_features_async(session: AsyncSession) -> Sequence[Feature]:
    """Get all features using async database operations for better concurrency."""

    statement: Final = select(Feature).where(
        Feature.deleted_at.is_(None)  # type: ignore[union-attr,attr-defined]
    )
    result = await session.execute(statement)
    features = result.scalars().all()
    return features  # type: ignore[no-any-return]


def get_feature(
    session: Session, name: str, item_id: int | None = None
) -> Feature | None:
    statement: Final = select(Feature).where(
        Feature.name == name,
        Feature.item_id == item_id,
        Feature.deleted_at.is_(None),  # type: ignore[union-attr,attr-defined]
    )
    results: Final = session.exec(statement)
    feature: Final = results.first()
    return feature  # type: ignore[no-any-return]


def get_feature_by_id(session: Session, feature_id: int) -> Feature | None:
    statement: Final = select(Feature).where(
        Feature.id == feature_id,
        Feature.deleted_at.is_(None),  # type: ignore[union-attr,attr-defined]
    )
    results: Final = session.exec(statement)
    feature: Final = results.first()
    return feature  # type: ignore[no-any-return]


def create_feature(session: Session, feature: Feature) -> tuple[Feature, str | None]:
    logger.debug(
        "Creating feature", feature_name=feature.name, created_by=feature.created_by
    )

    # Validate name using feature-specific validation function
    validate_entity_name_with_logging(feature.name, "feature")

    # Check if feature with same name and item_id already exists
    existing_feature: Final = get_feature(session, feature.name, feature.item_id)

    if existing_feature:
        # Calculate new amount, capping at MAX_FEATURE_AMOUNT
        new_amount = min(existing_feature.amount + feature.amount, MAX_FEATURE_AMOUNT)
        was_capped = (existing_feature.amount + feature.amount) > MAX_FEATURE_AMOUNT

        if new_amount > existing_feature.amount:
            # Update existing feature amount
            existing_feature.amount = new_amount
            session.add(existing_feature)
            session.commit()
            session.refresh(existing_feature)

            logger.info(
                "Feature amount increased",
                feature_name=feature.name,
                old_amount=existing_feature.amount - feature.amount,
                new_amount=new_amount,
            )

            if was_capped:
                message = (
                    f"{feature.name} amount capped at maximum ({MAX_FEATURE_AMOUNT}x)"
                )
                return existing_feature, message
            else:
                return existing_feature, None
        else:
            # Already at maximum amount
            logger.info(
                "Feature already at maximum amount",
                feature_name=feature.name,
                amount=existing_feature.amount,
            )
            message = (
                f"{feature.name} is already at maximum amount ({MAX_FEATURE_AMOUNT}x)"
            )
            return existing_feature, message

    # Create new feature if none exists
    commit_and_refresh_entity(session, feature)

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
    return feature, None


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
        # Import here to avoid circular imports
        from .item_service import get_item

        item = get_item(session=session, name=item_name)
        logger.debug("Found item for action", action=action, item=item)
        if item:
            item_id = item.id
    else:
        item_id = None

    feature = get_feature(session=session, name=name, item_id=item_id)
    logger.debug("Found feature for action", action=action, feature=feature)

    if feature:
        apply_veto_to_feature(session, feature, user, veto, item_name=item_name)
    else:
        logger.warning(
            f"Feature not found for {action}",
            extra={"feature_name": name, "item_name": item_name, "user": user},
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
        apply_veto_to_feature(session, feature, user, veto, feature_id=feature_id)
    else:
        logger.warning(
            f"Feature not found for {action}",
            extra={"feature_id": feature_id, "user": user},
        )

    return feature


def delete_feature(session: Session, feature_id: int) -> bool:
    """Soft delete a feature by ID.

    Args:
        session: Database session
        feature_id: ID of the feature to delete

    Returns:
        True if feature was deleted, False if not found
    """
    logger.debug("Soft deleting feature", feature_id=feature_id)

    feature: Final = get_feature_by_id(session, feature_id)
    if not feature:
        logger.warning("Feature deletion failed - not found", feature_id=feature_id)
        return False

    # Convert to domain entity and perform soft delete
    domain_feature = feature.to_domain()
    domain_feature.soft_delete()

    # Update the database model
    feature.deleted_at = domain_feature.deleted_at

    session.add(feature)
    session.commit()

    log_database_operation(
        operation="soft_delete",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature_id,
    )
    logger.info(
        "Feature soft deleted successfully",
        feature_name=feature.name,
        feature_id=feature_id,
    )
    return True


def restore_feature(session: Session, feature_id: int) -> bool:
    """Restore a soft deleted feature.

    Args:
        session: Database session
        feature_id: ID of the feature to restore

    Returns:
        True if feature was restored, False if not found
    """
    logger.debug("Restoring feature", feature_id=feature_id)

    # Look for soft deleted feature
    statement: Final = select(Feature).where(
        Feature.id == feature_id,
        Feature.deleted_at.is_not(None),  # type: ignore[union-attr,attr-defined]
    )
    results: Final = session.exec(statement)
    feature: Final = results.first()

    if not feature:
        logger.warning("Feature restore failed - not found", feature_id=feature_id)
        return False

    # Convert to domain entity and restore
    domain_feature = feature.to_domain()
    domain_feature.restore()

    # Update the database model
    feature.deleted_at = None

    session.add(feature)
    session.commit()

    log_database_operation(
        operation="restore",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature_id,
    )
    logger.info(
        "Feature restored successfully",
        feature_name=feature.name,
        feature_id=feature_id,
    )
    return True
