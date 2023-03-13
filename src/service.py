from typing import Final, Optional

from sqlmodel import select  # type: ignore
from sqlmodel import Session

from models import SVObject, SVProperty
from utils import logger


def get_objects(
    session: Session,
):
    statement: Final = select(SVObject)
    results: Final = session.exec(statement)
    objects: Final = results.all()
    return objects


def get_object(
    session: Session,
    name: str,
):
    statement: Final = select(SVObject).where(SVObject.name == name)
    results: Final = session.exec(statement)
    object: Final = results.first()
    return object


def create_object(
    session: Session,
    object: SVObject,
):
    same_name_object: Final = get_object(session, object.name)

    if not same_name_object:
        session.add(object)
        session.commit()
        session.refresh(object)

        return object

    else:
        return None


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
    obj_id: Optional[int] = None,
):
    statement: Final = select(SVProperty).where(
        SVProperty.name == name, SVProperty.object_id == obj_id
    )
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
        return {"error": "Property already exists"}


def veto_property_without_object(
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


def veto_object_property(
    session: Session,
    user: str,
    object_name: str,
    name: str,
):

    logger.info(f"veto_object_property {user=}, {object_name=}, {name=} ")

    object = get_object(session=session, name=object_name)
    logger.info(f"veto_object_property {object=}")

    if object:
        property = get_property(session=session, name=name, obj_id=object.id)
        logger.info(f"veto_object_property {property=}")

        if property:
            if user not in property.vetoed_by:
                property.vetoed_by = property.vetoed_by + [user]

            session.commit()
            session.refresh(property)

        return property
