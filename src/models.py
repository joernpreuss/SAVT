from typing import Optional
from sqlmodel import Field  # type: ignore
from sqlmodel import SQLModel

# later
# class SVUser(SQLModel, table=True):
#     """A user of the system."""

#     __tablename__ = "sv_users"
#     id: int = Field(primary_key=True)
#     name: str


# use later
class SVProperty(SQLModel, table=True):
    """A property of an object. Can be a topping of a pizza."""

    __tablename__ = "sv_properties"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_by: Optional[str] = None  # use SVUser later


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
