from sqlmodel import select  # type: ignore
from sqlmodel import Session

from models import SVProperty


def get_property(
    session: Session,
    name: str,
):
    statement = select(SVProperty).where(SVProperty.name == name)
    results = session.exec(statement)
    property = results.first()
    return property


def create_property(
    session: Session,
    property: SVProperty,
):
    same_name_property = get_property(session, property.name)

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
    property = get_property(session, name)

    if property:
        if user not in property.vetoed_by:
            property.vetoed_by = property.vetoed_by + [user]

        session.commit()
        session.refresh(property)

    return property
