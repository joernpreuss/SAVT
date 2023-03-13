from typing import List, Optional, Union

from fastapi import Form
from sqlmodel import Field  # type: ignore
from sqlmodel import Relationship  # type: ignore
from sqlmodel import JSON, Column, SQLModel

# later
# class SVUser(SQLModel, table=True):
#     """A user of the system."""

#     __tablename__ = "sv_users"
#     id: int = Field(primary_key=True)
#     name: str


# Use later for multiple objects (pizzas) with their own toppings
class SVObject(SQLModel, table=True):
    """An object with properties. Can be a pizza with toppings."""

    # __tablename__ = "sv_objects"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)

    name: str
    created_by: Optional[str] = None  # use SVUser later

    properties: List["SVProperty"] = Relationship(back_populates="object")

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
    ) -> "SVObject":
        return cls(name=name)


class SVProperty(SQLModel, table=True):
    """A property of an object. Can be a topping of a pizza."""

    # __tablename__ = "sv_properties"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_by: Optional[str] = None  # use SVUser later

    object_id: Optional[int] = Field(default=None, foreign_key="svobject.id")
    object: Optional[SVObject] = Relationship(back_populates="properties")

    # to have a list of users who vetoed this property that works with sqlite
    vetoed_by: list[str] = Field(default=[], sa_column=Column(JSON))

    # Needed for Column(JSON)
    class Config:  # type: ignore
        arbitrary_types_allowed = True

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        object_id: Optional[Union[int, str]] = Form(None),
    ) -> "SVProperty":
        if not object_id or not isinstance(object_id, int):
            return cls(name=name, object_id=None)
        else:
            return cls(name=name, object_id=object_id)
