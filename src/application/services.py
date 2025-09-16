"""Application layer - Use cases and business logic."""

from sqlmodel import Session

from ..domain.entities import Feature as DomainFeature
from ..domain.entities import Item as DomainItem
from ..domain.exceptions import ValidationError
from ..infrastructure.database.repositories import FeatureRepository, ItemRepository


class ItemService:
    """Application service for Item operations."""

    def __init__(self, session: Session):
        self.item_repo = ItemRepository(session)
        self.feature_repo = FeatureRepository(session)

    def create_item(
        self, name: str, kind: str | None = None, created_by: str | None = None
    ) -> DomainItem:
        """Create a new item with business logic validation."""
        # Domain entity validates business rules automatically
        domain_item = DomainItem(
            id=None,
            name=name.strip(),
            kind=kind.strip() if kind else None,
            created_by=created_by,
        )

        return self.item_repo.save(domain_item)

    def get_item_with_features(self, item_id: int) -> DomainItem | None:
        """Get item with all its features."""
        return self.item_repo.find_with_features(item_id)

    def get_all_items(self) -> list[DomainItem]:
        """Get all items."""
        return self.item_repo.find_all()


class FeatureService:
    """Application service for Feature operations."""

    def __init__(self, session: Session):
        self.feature_repo = FeatureRepository(session)

    def create_feature(
        self, name: str, item_id: int, amount: int = 1, created_by: str | None = None
    ) -> DomainFeature:
        """Create a new feature with business logic validation."""
        # Domain entity validates business rules automatically
        domain_feature = DomainFeature(
            id=None,
            name=name.strip(),
            amount=amount,
            item_id=item_id,
            created_by=created_by,
            vetoed_by=None,  # Will be initialized as empty list
        )

        return self.feature_repo.save(domain_feature)

    def veto_feature(self, feature_id: int, user: str) -> DomainFeature:
        """Add a veto to a feature."""
        domain_feature = self.feature_repo.find_by_id(feature_id)
        if not domain_feature:
            raise ValidationError(f"Feature {feature_id} not found")

        # Use domain entity method for business logic
        domain_feature.add_veto(user)

        return self.feature_repo.save(domain_feature)

    def unveto_feature(self, feature_id: int, user: str) -> DomainFeature:
        """Remove a veto from a feature."""
        domain_feature = self.feature_repo.find_by_id(feature_id)
        if not domain_feature:
            raise ValidationError(f"Feature {feature_id} not found")

        # Use domain entity method for business logic
        domain_feature.remove_veto(user)

        return self.feature_repo.save(domain_feature)

    def get_features_for_item(self, item_id: int) -> list[DomainFeature]:
        """Get all features for an item."""
        return self.feature_repo.find_by_item(item_id)

    def delete_feature(self, feature_id: int) -> bool:
        """Delete a feature."""
        return self.feature_repo.delete(feature_id)
