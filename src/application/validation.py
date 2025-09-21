"""Shared validation utilities for application layer.

This module provides common validation functions used across different services
to ensure consistent business rule enforcement and eliminate code duplication.
"""

from ..domain.entities import validate_entity_name
from ..domain.exceptions import ValidationError
from ..logging_config import get_logger

logger = get_logger(__name__)


def validate_entity_name_with_logging(name: str, entity_type: str = "entity") -> None:
    """Validate entity name with logging for application layer.

    Args:
        name: The name to validate
        entity_type: Type of entity being validated (for error messages)

    Raises:
        ValueError: If name is empty, too long, or contains problematic characters
    """
    try:
        validate_entity_name(name, entity_type)
    except ValidationError as e:
        # Log validation failures for monitoring
        if "empty" in str(e):
            logger.warning(
                f"{entity_type.title()} creation failed - empty name provided",
                attempted_name=repr(name),
                entity_type=entity_type,
            )
        elif "longer" in str(e):
            logger.warning(
                f"{entity_type.title()} creation failed - name too long",
                name_length=len(name),
                entity_type=entity_type,
            )
        elif "control characters" in str(e):
            logger.warning(
                f"{entity_type.title()} creation failed - contains problematic "
                + "character",
                attempted_name=repr(name),
                entity_type=entity_type,
            )

        # Convert ValidationError to ValueError for backward compatibility
        raise ValueError(str(e)) from e
