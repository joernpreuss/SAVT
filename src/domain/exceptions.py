"""Domain-specific exceptions."""


class DomainError(Exception):
    """Base exception for domain errors."""

    pass


class ValidationError(DomainError):
    """Raised when domain validation fails."""

    pass


class ItemAlreadyExistsError(DomainError):
    """Raised when attempting to create a duplicate item."""

    pass


class FeatureAlreadyExistsError(DomainError):
    """Raised when attempting to create a duplicate feature."""

    pass
