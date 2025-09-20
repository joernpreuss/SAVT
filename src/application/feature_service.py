# pyright: reportImportCycles=false
from collections.abc import Sequence
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session, select

from ..domain.constants import MAX_FEATURE_AMOUNT
from ..infrastructure.database.models import Feature
from ..logging_config import get_logger
from ..logging_utils import log_database_operation, log_user_action
from ..utils import apply_veto_to_feature
from .validation import validate_entity_name

logger: Final = get_logger(__name__)


class FeatureAlreadyExistsError(ValueError):
    pass


def _validate_feature_name(name: str) -> None:
    """Validate feature name using shared validation logic.

    Args:
        name: The name to validate

    Raises:
        ValueError: If name is empty, too long, or contains problematic characters
    """
    validate_entity_name(name, "feature")


def _commit_and_refresh_feature(session: Session, feature: Feature) -> Feature:
    """Common pattern for committing and refreshing features.

    Args:
        session: Database session
        feature: Feature to commit and refresh

    Returns:
        The refreshed feature
    """
    session.add(feature)
    session.commit()
    session.refresh(feature)
    return feature


def get_features(session: Session) -> Sequence[Feature]:
    statement: Final = select(Feature)
    results: Final = session.exec(statement)
    features: Final = results.all()
    return features  # type: ignore[no-any-return]


async def get_features_async(session: AsyncSession) -> Sequence[Feature]:
    """Get all features using async database operations for better concurrency."""

    statement: Final = select(Feature)
    result = await session.execute(statement)
    features = result.scalars().all()
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


def create_feature(session: Session, feature: Feature) -> tuple[Feature, str | None]:
    logger.debug(
        "Creating feature", feature_name=feature.name, created_by=feature.created_by
    )

    # Validate name using feature-specific validation function
    _validate_feature_name(feature.name)

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
    _commit_and_refresh_feature(session, feature)

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
    """Delete a feature by ID.

    Args:
        session: Database session
        feature_id: ID of the feature to delete

    Returns:
        True if feature was deleted, False if not found
    """
    logger.debug("Deleting feature", feature_id=feature_id)

    feature: Final = get_feature_by_id(session, feature_id)
    if not feature:
        logger.warning("Feature deletion failed - not found", feature_id=feature_id)
        return False

    # Store for undo before deletion
    feature_copy = Feature(
        name=feature.name,
        amount=feature.amount,
        created_by=feature.created_by,
        vetoed_by=feature.vetoed_by.copy(),
        item_id=feature.item_id,
    )
    # Store the original ID for undo reference
    feature_copy.id = feature.id

    # Import here to avoid circular imports
    from .undo_service import store_deleted_feature

    store_deleted_feature(feature_copy)

    # Delete the feature
    session.delete(feature)
    session.commit()

    log_database_operation(
        operation="delete",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature_id,
    )
    logger.info(
        "Feature deleted successfully", feature_name=feature.name, feature_id=feature_id
    )
    return True
