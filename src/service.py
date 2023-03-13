from typing import Final, Optional

from sqlmodel import select  # type: ignore
from sqlmodel import Session

from models import SVObject, SVProperty
from utils import logger


def get_objects(session: Session):
    statement: Final = select(SVObject)
    results: Final = session.exec(statement)
    objects: Final = results.all()
    return objects


def get_object(session: Session, name: str):
    statement: Final = select(SVObject).where(SVObject.name == name)
    results: Final = session.exec(statement)
    obj: Final = results.first()
    return obj


def create_object(session: Session, obj: SVObject):
    same_name_object: Final = get_object(session, obj.name)

    if not same_name_object:
        session.add(obj)
        session.commit()
        session.refresh(obj)
        return obj
    else:
        return {"error": "Property already exists"}


def get_properties(session: Session):
    statement: Final = select(SVProperty)
    results: Final = session.exec(statement)
    properties: Final = results.all()
    return properties


def get_property(session: Session, name: str, obj_id: Optional[int] = None):
    statement: Final = select(SVProperty).where(
        SVProperty.name == name, SVProperty.object_id == obj_id
    )
    results: Final = session.exec(statement)
    property: Final = results.first()
    return property


def create_property(session: Session, property: SVProperty):
    same_name_property: Final = get_property(session, property.name)

    if not same_name_property:
        session.add(property)
        session.commit()
        session.refresh(property)

        return property

    else:
        return {"error": "Property already exists"}


def veto_object_property(
    session: Session,
    user: str,
    name: str,
    object_name: Optional[str] = None,
    veto: bool = True,
):

    logger.info(f"veto_object_property {user=}, {object_name=}, {name=}")

    if object_name:
        object = get_object(session=session, name=object_name)
        logger.info(f"veto_object_property {object=}")

        if object:
            object_id = object.id
        else:
            object_id = None
    else:
        object_id = None

    property = get_property(session=session, name=name, obj_id=object_id)
    logger.info(f"veto_object_property                    {property=}")

    if property:
        if veto:
            if user not in property.vetoed_by:
                property.vetoed_by = property.vetoed_by + [user]
        else:
            if user in property.vetoed_by:
                # tmp = property.vetoed_by
                # tmp.remove(user)
                property.vetoed_by = [u for u in property.vetoed_by if u != user]

        logger.info(f"veto_object_property before refresh {property=}")
        session.commit()
        session.refresh(property)
        logger.info(f"veto_object_property after  refresh {property=}")

    return property
