from fastapi import Form
from sqlmodel import (
    JSON,
    Column,
    Field,
    Relationship,
    SQLModel,
)

from .constants import MAX_KIND_LENGTH, MAX_NAME_LENGTH

# later
# class SVUser(SQLModel, table=True):
#     """A user of the system."""

#     __tablename__ = "sv_users"
#     id: int = Field(primary_key=True)
#     name: str


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


class Feature(SQLModel, table=True):  # type: ignore[call-arg]
    """A feature of an item. Can be a topping of a pizza."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=MAX_NAME_LENGTH)
    created_by: str | None = None  # use SVUser later

    # to have a list of users who vetoed this feature that works with sqlite
    vetoed_by: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    item_id: int | None = Field(default=None, foreign_key="item.id", index=True)
    item: Item | None = Relationship(back_populates="features")

    # JSON Column works without special config in current setup

    @classmethod
    def as_form(
        cls, name: str = Form(...), item_id: int | str | None = Form(None)
    ) -> "Feature":
        # Form values arrive as strings; convert to int if possible
        if isinstance(item_id, str):
            item_id = int(item_id) if item_id.isdigit() else None
        return cls(name=name, item_id=item_id if isinstance(item_id, int) else None)
