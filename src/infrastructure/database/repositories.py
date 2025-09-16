"""Infrastructure layer - Repository implementations."""

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ...domain.entities import Feature as DomainFeature
from ...domain.entities import Item as DomainItem
from ...domain.exceptions import FeatureAlreadyExistsError, ItemAlreadyExistsError
from .models import Feature as FeatureModel
from .models import Item as ItemModel


class ItemRepository:
    """Repository for Item persistence operations."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, domain_item: DomainItem) -> DomainItem:
        """Save domain item to database."""
        item_model = ItemModel.from_domain(domain_item)

        if item_model.id is None:
            # New item - check for duplicates
            existing = self.session.exec(
                select(ItemModel).where(ItemModel.name == item_model.name)
            ).first()
            if existing:
                raise ItemAlreadyExistsError(f"Item '{item_model.name}' already exists")

        self.session.add(item_model)
        self.session.commit()
        self.session.refresh(item_model)

        return item_model.to_domain()

    def find_by_id(self, item_id: int) -> DomainItem | None:
        """Find item by ID."""
        item_model = self.session.get(ItemModel, item_id)
        return item_model.to_domain() if item_model else None

    def find_all(self) -> list[DomainItem]:
        """Get all items."""
        items = self.session.exec(select(ItemModel)).all()
        return [item.to_domain() for item in items]

    def find_with_features(self, item_id: int) -> DomainItem | None:
        """Find item with its features loaded."""
        item_model = self.session.exec(
            select(ItemModel)
            .options(selectinload(ItemModel.features))
            .where(ItemModel.id == item_id)
        ).first()
        return item_model.to_domain() if item_model else None


class FeatureRepository:
    """Repository for Feature persistence operations."""

    def __init__(self, session: Session):
        self.session = session

    def save(self, domain_feature: DomainFeature) -> DomainFeature:
        """Save domain feature to database."""
        feature_model = FeatureModel.from_domain(domain_feature)

        if feature_model.id is None:
            # New feature - check for duplicates within same item
            existing = self.session.exec(
                select(FeatureModel).where(
                    FeatureModel.name == feature_model.name,
                    FeatureModel.item_id == feature_model.item_id,
                )
            ).first()
            if existing:
                raise FeatureAlreadyExistsError(
                    f"Feature '{feature_model.name}' already exists for this item"
                )

        self.session.add(feature_model)
        self.session.commit()
        self.session.refresh(feature_model)

        return feature_model.to_domain()

    def find_by_id(self, feature_id: int) -> DomainFeature | None:
        """Find feature by ID."""
        feature_model = self.session.get(FeatureModel, feature_id)
        return feature_model.to_domain() if feature_model else None

    def find_by_item(self, item_id: int) -> list[DomainFeature]:
        """Get all features for an item."""
        features = self.session.exec(
            select(FeatureModel).where(FeatureModel.item_id == item_id)
        ).all()
        return [feature.to_domain() for feature in features]

    def delete(self, feature_id: int) -> bool:
        """Delete feature by ID."""
        feature_model = self.session.get(FeatureModel, feature_id)
        if feature_model:
            self.session.delete(feature_model)
            self.session.commit()
            return True
        return False
