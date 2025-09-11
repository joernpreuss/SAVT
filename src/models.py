from fastapi import Form
from pydantic import ConfigDict
from sqlmodel import (
    JSON,
    Column,
    Field,  # type: ignore
    Relationship,  # type: ignore
    SQLModel,
)

# later
# class SVUser(SQLModel, table=True):
#     """A user of the system."""

#     __tablename__ = "sv_users"
#     id: int = Field(primary_key=True)
#     name: str


class SVObject(SQLModel, table=True):  # type: ignore[call-arg]
    """An object with properties. Can be a pizza with toppings."""

    # __tablename__ = "sv_objects"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_by: str | None = None  # use SVUser later

    properties: list["SVProperty"] = Relationship(back_populates="object")

    @classmethod
    def as_form(cls, name: str = Form(...)) -> "SVObject":
        return cls(name=name)


class SVProperty(SQLModel, table=True):  # type: ignore[call-arg]
    """A property of an object. Can be a topping of a pizza."""

    # __tablename__ = "sv_properties"  # type: ignore

    id: int | None = Field(default=None, primary_key=True)
    name: str
    created_by: str | None = None  # use SVUser later

    # to have a list of users who vetoed this property that works with sqlite
    vetoed_by: list[str] = Field(default=[], sa_column=Column(JSON))

    object_id: int | None = Field(default=None, foreign_key="svobject.id")
    object: SVObject | None = Relationship(back_populates="properties")

    # Needed for Column(JSON)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def as_form(
        cls, name: str = Form(...), object_id: int | str | None = Form(None)
    ) -> "SVProperty":
        if not object_id or not isinstance(object_id, int):
            return cls(name=name, object_id=None)
        else:
            return cls(name=name, object_id=object_id)
