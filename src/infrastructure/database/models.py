from fastapi import Form
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from ...domain.constants import MAX_FEATURE_AMOUNT, MAX_KIND_LENGTH, MAX_NAME_LENGTH
from ...domain.entities import Feature as DomainFeature
from ...domain.entities import Item as DomainItem


class Item(SQLModel, table=True):  # type: ignore[call-arg]
    """An item with features. Can be a pizza with toppings."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=MAX_NAME_LENGTH)
    kind: str | None = Field(
        default=None, max_length=MAX_KIND_LENGTH
    )  # e.g., vegan, vegetarian
    created_by: str | None = None  # use SVUser later

    features: list["Feature"] = Relationship(back_populates="item")

    @classmethod
    def as_form(cls, name: str = Form(...), kind: str | None = Form(None)) -> "Item":
        return cls(name=name, kind=kind)

    @classmethod
    def from_domain(cls, domain_item: DomainItem) -> "Item":
        """Convert domain entity to persistence model."""
        return cls(
            id=domain_item.id,
            name=domain_item.name,
            kind=domain_item.kind,
            created_by=domain_item.created_by,
        )

    def to_domain(self) -> DomainItem:
        """Convert persistence model to domain entity."""
        return DomainItem(
            id=self.id,
            name=self.name,
            kind=self.kind,
            created_by=self.created_by,
        )


class Feature(SQLModel, table=True):  # type: ignore[call-arg]
    """A feature of an item. Can be a topping of a pizza."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=MAX_NAME_LENGTH)
    amount: int = Field(default=1, ge=1, le=MAX_FEATURE_AMOUNT)
    created_by: str | None = None  # use SVUser later

    # to have a list of users who vetoed this feature that works with sqlite
    vetoed_by: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    item_id: int | None = Field(default=None, foreign_key="item.id", index=True)
    item: Item | None = Relationship(back_populates="features")

    # JSON Column works without special config in current setup

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        amount: int = Form(1),
        item_id: int | str | None = Form(None),
    ) -> "Feature":
        # Form values arrive as strings; convert to int if possible
        if isinstance(item_id, str):
            item_id = int(item_id) if item_id.isdigit() else None
        return cls(
            name=name,
            amount=amount,
            item_id=item_id if isinstance(item_id, int) else None,
        )

    @classmethod
    def from_domain(cls, domain_feature: DomainFeature) -> "Feature":
        """Convert domain entity to persistence model."""
        return cls(
            id=domain_feature.id,
            name=domain_feature.name,
            amount=domain_feature.amount,
            created_by=domain_feature.created_by,
            vetoed_by=domain_feature.vetoed_by or [],
            item_id=domain_feature.item_id,
        )

    def to_domain(self) -> DomainFeature:
        """Convert persistence model to domain entity."""
        return DomainFeature(
            id=self.id,
            name=self.name,
            amount=self.amount,
            created_by=self.created_by,
            vetoed_by=self.vetoed_by,
            item_id=self.item_id,
        )
