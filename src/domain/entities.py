"""Pure domain entities without infrastructure dependencies."""

from dataclasses import dataclass
from datetime import datetime

from .constants import MAX_FEATURE_AMOUNT, MAX_KIND_LENGTH, MAX_NAME_LENGTH
from .exceptions import ValidationError


@dataclass
class Item:
    """Core business entity representing an item (e.g., pizza)."""

    id: int | None
    name: str
    kind: str | None = None
    created_by: str | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        """Validate item data after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate item business rules."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValidationError("Item name cannot be empty")

        if len(self.name) > MAX_NAME_LENGTH:
            raise ValidationError(
                f"Item name cannot exceed {MAX_NAME_LENGTH} characters"
            )

        if self.kind and len(self.kind) > MAX_KIND_LENGTH:
            raise ValidationError(
                f"Item kind cannot exceed {MAX_KIND_LENGTH} characters"
            )

    def is_deleted(self) -> bool:
        """Check if item is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark item as deleted with current timestamp."""
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore soft deleted item."""
        self.deleted_at = None


@dataclass
class Feature:
    """Core business entity representing a feature (e.g., topping)."""

    id: int | None
    name: str
    amount: int = 1
    created_by: str | None = None
    deleted_at: datetime | None = None
    vetoed_by: list[str] | None = None
    item_id: int | None = None

    def __post_init__(self):
        """Initialize defaults and validate after creation."""
        if self.vetoed_by is None:
            self.vetoed_by = []
        self.validate()

    def validate(self) -> None:
        """Validate feature business rules."""
        if not self.name or len(self.name.strip()) == 0:
            raise ValidationError("Feature name cannot be empty")

        if len(self.name) > MAX_NAME_LENGTH:
            raise ValidationError(
                f"Feature name cannot exceed {MAX_NAME_LENGTH} characters"
            )

        if self.amount < 1 or self.amount > MAX_FEATURE_AMOUNT:
            raise ValidationError(
                f"Feature amount must be between 1 and {MAX_FEATURE_AMOUNT}"
            )

    def is_vetoed_by(self, user: str) -> bool:
        """Check if feature is vetoed by a specific user."""
        return user in (self.vetoed_by or [])

    def add_veto(self, user: str) -> None:
        """Add a veto from a user."""
        if self.vetoed_by is None:
            self.vetoed_by = []
        if user not in self.vetoed_by:
            self.vetoed_by.append(user)

    def remove_veto(self, user: str) -> None:
        """Remove a veto from a user."""
        if self.vetoed_by and user in self.vetoed_by:
            self.vetoed_by.remove(user)

    def is_vetoed(self) -> bool:
        """Check if feature has any vetoes."""
        return bool(self.vetoed_by)

    def is_deleted(self) -> bool:
        """Check if feature is soft deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark feature as deleted with current timestamp."""
        self.deleted_at = datetime.now()

    def restore(self) -> None:
        """Restore soft deleted feature."""
        self.deleted_at = None
