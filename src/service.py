from typing import Final
from collections.abc import Sequence

from sqlmodel import (
    Session,
    select,
)
from sqlalchemy.orm import selectinload

from .logging_config import get_logger
from .logging_utils import log_database_operation, log_user_action
from .models import SVObject, SVProperty

logger = get_logger(__name__)


class ObjectAlreadyExistsError(ValueError):
    pass


class PropertyAlreadyExistsError(ValueError):
    pass


def get_objects(session: Session) -> Sequence[SVObject]:
    statement: Final = select(SVObject).options(selectinload(SVObject.properties))
    results: Final = session.exec(statement)
    objects: Final = results.all()
    return objects  # type: ignore[no-any-return]


def get_object(session: Session, name: str) -> SVObject | None:
    statement: Final = select(SVObject).where(SVObject.name == name)
    results: Final = session.exec(statement)
    obj: Final = results.first()
    return obj  # type: ignore[no-any-return]


def create_object(session: Session, obj: SVObject) -> SVObject:
    logger.debug(f"Creating object: {obj.name}")
    
    # Validate that name is not empty
    if not obj.name or not obj.name.strip():
        logger.warning("Object creation failed - empty name provided")
        raise ValueError("Object name cannot be empty")
    
    same_name_object: Final = get_object(session, obj.name)

    if not same_name_object:
        session.add(obj)
        session.commit()
        session.refresh(obj)

        log_database_operation(
            operation="create",
            table="SVObject",
            success=True,
            object_name=obj.name,
            object_id=obj.id,
        )
        logger.info(f"Object created successfully: {obj.name}")
        return obj
    else:
        logger.warning(f"Object creation failed - already exists: {obj.name}")
        raise ObjectAlreadyExistsError(f"Object with name '{obj.name}' already exists")


def get_properties(session: Session) -> Sequence[SVProperty]:
    statement: Final = select(SVProperty)
    results: Final = session.exec(statement)
    properties: Final = results.all()
    return properties  # type: ignore[no-any-return]


def get_property(session: Session, name: str, obj_id: int | None = None) -> SVProperty | None:
    statement: Final = select(SVProperty).where(
        SVProperty.name == name, SVProperty.object_id == obj_id
    )
    results: Final = session.exec(statement)
    prop: Final = results.first()
    return prop  # type: ignore[no-any-return]


def create_property(session: Session, prop: SVProperty) -> SVProperty:
    logger.debug(f"Creating property: {prop.name} (created_by: {prop.created_by})")
    same_name_property: Final = get_property(session, prop.name)

    if not same_name_property:
        session.add(prop)
        session.commit()
        session.refresh(prop)

        log_database_operation(
            operation="create",
            table="SVProperty",
            success=True,
            property_name=prop.name,
            property_id=prop.id,
            created_by=prop.created_by,
        )

        if prop.created_by:
            log_user_action(
                action="create_property",
                user=prop.created_by,
                property_name=prop.name,
                property_id=prop.id,
            )

        logger.info(f"Property created successfully: {prop.name}")
        return prop

    else:
        logger.warning(f"Property creation failed - already exists: {prop.name}")
        raise PropertyAlreadyExistsError(
            f"Property with name '{prop.name}' already exists"
        )


def veto_object_property(
    session: Session,
    user: str,
    name: str,
    object_name: str | None = None,
    veto: bool = True,
) -> SVProperty | None:
    action = "veto" if veto else "unveto"
    logger.debug(
        f"Processing {action} for user={user}, property={name}, object={object_name}"
    )

    object_id = None
    if object_name:
        obj = get_object(session=session, name=object_name)
        logger.debug(f"Found object for {action}: {obj}")
        if obj:
            object_id = obj.id
    else:
        object_id = None

    prop = get_property(session=session, name=name, obj_id=object_id)
    logger.debug(f"Found property for {action}: {prop}")

    if prop:
        vetoed_by_set = set(prop.vetoed_by)
        original_vetoed_by = set(prop.vetoed_by)

        if veto:
            vetoed_by_set.add(user)
        else:
            vetoed_by_set.discard(user)

        # Only update if there's a change
        if original_vetoed_by != vetoed_by_set:
            prop.vetoed_by = sorted(vetoed_by_set)

            logger.debug(
                f"Updating property vetoed_by from {sorted(original_vetoed_by)} to {prop.vetoed_by}"
            )
            session.commit()
            session.refresh(prop)

            log_database_operation(
                operation="update",
                table="SVProperty",
                success=True,
                property_name=prop.name,
                property_id=prop.id,
                action=action,
            )

            log_user_action(
                action=f"{action}_property",
                user=user,
                property_name=prop.name,
                object_name=object_name,
                vetoed_by_count=len(prop.vetoed_by),
            )

            logger.info(f"Property {action}ed successfully by {user}: {prop.name}")
        else:
            logger.debug(f"No change needed for {action} by {user}: {prop.name}")
    else:
        logger.warning(
            f"Property not found for {action}",
            extra={"property_name": name, "object_name": object_name, "user": user},
        )

    return prop
