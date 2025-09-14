import logging
import sys
from typing import Final

from .constants import MAX_NAME_LENGTH

logger: Final = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)


def truncate_name(name: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """Truncate a name to fit within max_length using first_chars...last_chars format.

    Args:
        name: The name to potentially truncate
        max_length: Maximum allowed length (default: MAX_NAME_LENGTH)

    Returns:
        Original name if it fits, or truncated name with ... in the middle
    """
    if len(name) <= max_length:
        return name

    # Reserve 3 characters for "..."
    available_chars = max_length - 3

    # Split available characters between first and last parts
    first_chars = available_chars // 2
    last_chars = available_chars - first_chars

    return f"{name[:first_chars]}...{name[-last_chars:]}"


def apply_veto_to_feature(
    session,
    feature,
    user: str,
    veto: bool,
    item_name: str | None = None,
    feature_id: int | None = None,
) -> bool:
    """Apply veto/unveto logic to a feature and handle all database/logging operations.

    Args:
        session: Database session
        feature: Feature object to modify
        user: User performing the action
        veto: True for veto, False for unveto
        item_name: Optional item name for logging
        feature_id: Optional feature ID for logging

    Returns:
        True if the feature was modified, False if no change was needed
    """
    from .logging_config import get_logger
    from .logging_utils import log_database_operation, log_user_action

    logger = get_logger(__name__)
    action = "veto" if veto else "unveto"

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

        log_user_action_kwargs = {
            "action": f"{action}_feature",
            "user": user,
            "feature_name": feature.name,
            "vetoed_by_count": len(feature.vetoed_by),
        }
        if item_name is not None:
            log_user_action_kwargs["item_name"] = item_name
        if feature_id is not None:
            log_user_action_kwargs["feature_id"] = feature_id

        log_user_action(**log_user_action_kwargs)

        logger.info(
            "Feature action completed successfully",
            action=action,
            user=user,
            feature_name=feature.name,
        )
        return True
    else:
        logger.debug(
            "No change needed for action",
            action=action,
            user=user,
            feature_name=feature.name,
        )
        return False
