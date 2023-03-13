from typing import Optional

from fastapi import Form
from sqlmodel import Field  # type: ignore
from sqlmodel import JSON, Column, SQLModel

# later
# class SVUser(SQLModel, table=True):
#     """A user of the system."""

#     __tablename__ = "sv_users"
#     id: int = Field(primary_key=True)
#     name: str


class SVProperty(SQLModel, table=True):
    """A property of an object. Can be a topping of a pizza."""

    __tablename__ = "sv_properties"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_by: Optional[str] = None  # use SVUser later

    # to have a list of users who vetoed this property that works with sqlite
    vetoed_by: list[str] = Field(default=[], sa_column=Column(JSON))

    # Needed for Column(JSON)
    class Config:  # type: ignore
        arbitrary_types_allowed = True

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
    ) -> "SVProperty":
        return cls(name=name)


# Use later for multiple objects (pizzas) with their own toppings
# does not work yet
#
# class SVObject(SQLModel, table=True):
#     """An object with properties. Can be a pizza with toppings."""

#     __tablename__ = "sv_objects"  # type: ignore

#     id: Optional[int] = Field(default=None, primary_key=True)

#     name: str
#     created_by: Optional[str] = None  # use SVUser later

#     properties: List[SVProperty] = Relationship(
#         back_populates="sv_objects",
#     )
