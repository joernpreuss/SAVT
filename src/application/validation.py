"""Shared validation utilities for application layer.

This module provides common validation functions used across different services
to ensure consistent business rule enforcement and eliminate code duplication.
"""

from ..domain.constants import MAX_NAME_LENGTH
from ..logging_config import get_logger

logger = get_logger(__name__)


def validate_entity_name(name: str, entity_type: str = "entity") -> None:
    """Validate entity name according to business rules.

    Args:
        name: The name to validate
        entity_type: Type of entity being validated (for error messages)

    Raises:
        ValueError: If name is empty, too long, or contains problematic characters
    """
    if not name or not name.strip():
        logger.warning(
            f"{entity_type.title()} creation failed - empty name provided",
            attempted_name=repr(name),
            entity_type=entity_type,
        )
        raise ValueError(f"{entity_type.title()} name cannot be empty")

    if len(name) > MAX_NAME_LENGTH:
        logger.warning(
            f"{entity_type.title()} creation failed - name too long",
            name_length=len(name),
            entity_type=entity_type,
        )
        raise ValueError(
            f"{entity_type.title()} name cannot be longer than {MAX_NAME_LENGTH} "
            + "characters"
        )

    # Check for problematic control characters
    for char in name:
        if (ord(char) < 32 and char not in [" "]) or ord(char) == 127:
            # Allow space (ord 32), reject control chars and DEL (ord 127)
            logger.warning(
                f"{entity_type.title()} creation failed - contains problematic "
                + "character",
                attempted_name=repr(name),
                problematic_char=repr(char),
                entity_type=entity_type,
            )
            raise ValueError(
                f"{entity_type.title()} name cannot contain newlines, tabs, "
                + "or other control characters"
            )
