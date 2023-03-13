from sqlmodel import Session

from models import SVObject, SVProperty
from service import create_object, create_property


def test_create_object_with_property(
    session: Session,
    timestamp_str: str,
):
    object = SVObject(
        name=f"test_object_{timestamp_str}",
    )
    create_object(session, object)
    assert object.id is not None

    property = SVProperty(
        name=f"test_property_{timestamp_str}",
        object_id=object.id,
    )
    create_property(session, property)
    assert property.id is not None


def test_create_property_without_object(
    session: Session,
    timestamp_str: str,
):

    property = SVProperty(
        name=f"test_property_{timestamp_str}",
    )
    create_property(session, property)
    assert property.id is not None
