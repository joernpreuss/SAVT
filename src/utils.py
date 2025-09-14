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


def smart_shorten_name(name: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """Intelligently shorten complex merged names with better logic.

    Handles cases like "TestPizza2-1-TestPizza1-3-TestPizza1-2" by:
    1. Detecting repeated base names and consolidating them
    2. Using abbreviations for common patterns
    3. Falling back to regular truncation if needed

    Args:
        name: The name to shorten
        max_length: Maximum allowed length

    Returns:
        Shortened name that's more readable than simple truncation
    """
    if len(name) <= max_length:
        return name

    # Strategy 1: Try to consolidate repeated base names
    # Example: "TestPizza2-1-TestPizza1-3-TestPizza1-2" -> "TestPizza+3merged"
    shortened = _consolidate_repeated_names(name, max_length)
    if len(shortened) <= max_length:
        return shortened

    # Strategy 2: Use abbreviations for common patterns
    # Example: "VeryLongPizzaNameHere-Merge-AnotherLong" -> "VLPNameHere+ALong"
    shortened = _abbreviate_long_parts(name, max_length)
    if len(shortened) <= max_length:
        return shortened

    # Strategy 3: Fall back to regular truncation
    return truncate_name(name, max_length)


def _consolidate_repeated_names(name: str, max_length: int) -> str:
    """Consolidate repeated base names in merged item names."""
    import re
    from collections import Counter

    # Split on common separators used in merges
    parts = re.split(r"[-_+]", name)

    if len(parts) < 3:  # Not a complex merge, skip
        return name

    # Count base names (ignoring trailing numbers)
    base_names = []
    for part in parts:
        # Remove trailing numbers like "-1", "-2", etc.
        base = re.sub(r"-?\d+$", "", part)
        if base:  # Only add non-empty bases
            base_names.append(base)

    if not base_names:
        return name

    base_counts = Counter(base_names)

    # If we have repeated base names, consolidate them
    most_common_base, count = base_counts.most_common(1)[0]

    if count > 1:
        # Use the most common base + merge indicator
        other_bases = [base for base in base_counts.keys() if base != most_common_base]

        if other_bases:
            # Format: "MainBase+2others" or "MainBase+AnotherBase"
            if len(other_bases) == 1:
                other_name = other_bases[0][:10]  # Limit other name length
                consolidated = f"{most_common_base}+{other_name}"
            else:
                consolidated = f"{most_common_base}+{len(other_bases)}others"
        else:
            # All parts are the same base
            consolidated = f"{most_common_base}x{count}"

        return consolidated

    return name


def _abbreviate_long_parts(name: str, max_length: int) -> str:
    """Create abbreviations for long parts of a name."""
    import re

    # Split on common separators
    parts = re.split(r"([-_+])", name)

    abbreviated_parts = []

    for part in parts:
        if part in ["-", "_", "+"]:  # Keep separators
            abbreviated_parts.append(part)
        elif len(part) > 8:  # Abbreviate long parts
            # Create abbreviation: take first letter of each capital + first few chars
            capitals = re.findall(r"[A-Z]", part)
            if len(capitals) > 1:
                # CamelCase: "TestPizza" -> "TP"
                abbrev = "".join(capitals)
            else:
                # Single word: "verylongname" -> "verylong"
                abbrev = part[:6]
            abbreviated_parts.append(abbrev)
        else:
            abbreviated_parts.append(part)

    result = "".join(abbreviated_parts)

    # If still too long, truncate
    if len(result) > max_length:
        return truncate_name(result, max_length)

    return result


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
