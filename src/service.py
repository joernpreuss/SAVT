from sqlmodel import select  # type: ignore
from sqlmodel import Session

from models import SVProperty


def veto(
    session: Session,
    user: str,
    name: str,
):
    statement = select(SVProperty).where(SVProperty.name == name)
    results = session.exec(statement)
    property = results.one()

    if property:
        if user not in property.vetoed_by:
            property.vetoed_by = property.vetoed_by + [user]

        session.commit()
        session.refresh(property)

    return property
