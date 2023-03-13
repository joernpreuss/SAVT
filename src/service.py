from typing import Final

from sqlmodel import select  # type: ignore
from sqlmodel import Session

from models import SVProperty


def get_properties(
    session: Session,
):
    statement: Final = select(SVProperty)
    results: Final = session.exec(statement)
    properties: Final = results.all()
    return properties


def get_property(
    session: Session,
    name: str,
):
    statement: Final = select(SVProperty).where(SVProperty.name == name)
    results: Final = session.exec(statement)
    property: Final = results.first()
    return property


def create_property(
    session: Session,
    property: SVProperty,
):
    same_name_property: Final = get_property(session, property.name)

    if not same_name_property:
        session.add(property)
        session.commit()
        session.refresh(property)

        return property

    else:
        return None


def veto_property(
    session: Session,
    user: str,
    name: str,
):
    property: Final = get_property(session, name)

    if property:
        if user not in property.vetoed_by:
            property.vetoed_by = property.vetoed_by + [user]

        session.commit()
        session.refresh(property)

    return property
