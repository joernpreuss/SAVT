from typing import Final

from sqlmodel import (
    Session,
    select,  # type: ignore
)

from .models import SVObject, SVProperty
from .utils import logger


class ObjectAlreadyExistsError(ValueError):
    pass


class PropertyAlreadyExistsError(ValueError):
    pass


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
        raise ObjectAlreadyExistsError(f"Object with name '{obj.name}' already exists")


def get_properties(session: Session):
    statement: Final = select(SVProperty)
    results: Final = session.exec(statement)
    properties: Final = results.all()
    return properties


def get_property(session: Session, name: str, obj_id: int | None = None):
    statement: Final = select(SVProperty).where(
        SVProperty.name == name, SVProperty.object_id == obj_id
    )
    results: Final = session.exec(statement)
    prop: Final = results.first()
    return prop


def create_property(session: Session, prop: SVProperty):
    same_name_property: Final = get_property(session, prop.name)

    if not same_name_property:
        session.add(prop)
        session.commit()
        session.refresh(prop)

        return prop

    else:
        raise PropertyAlreadyExistsError(
            f"Property with name '{prop.name}' already exists"
        )


def veto_object_property(
    session: Session,
    user: str,
    name: str,
    object_name: str | None = None,
    veto: bool = True,
):
    logger.info(f"veto_object_property {user=}, {object_name=}, {name=}")

    object_id = None
    if object_name:
        obj = get_object(session=session, name=object_name)
        logger.info(f"veto_object_property {obj=}")
        if obj:
            object_id = obj.id
    else:
        object_id = None

    prop = get_property(session=session, name=name, obj_id=object_id)
    logger.info(f"veto_object_property                    {prop=}")

    if prop:
        vetoed_by_set = set(prop.vetoed_by)
        if veto:
            vetoed_by_set.add(user)
        else:
            vetoed_by_set.discard(user)

        if set(prop.vetoed_by) != vetoed_by_set:
            prop.vetoed_by = sorted(vetoed_by_set)

            logger.info(f"veto_object_property before refresh {prop=}")
            session.commit()
            session.refresh(prop)
            logger.info(f"veto_object_property after  refresh {prop=}")

    return prop
