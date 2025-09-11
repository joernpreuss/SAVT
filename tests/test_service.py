from sqlmodel import Session

from src.models import SVObject, SVProperty
from src.service import create_object, create_property


def test_create_object_with_property(
    session: Session,
    timestamp_str: str,
):
    obj = SVObject(
        name=f"test_object_{timestamp_str}",
    )
    create_object(session, obj)
    assert obj.id is not None

    prop = SVProperty(
        name=f"test_property_{timestamp_str}",
        object_id=obj.id,
    )
    create_property(session, prop)
    assert prop.id is not None


def test_create_property_without_object(
    session: Session,
    timestamp_str: str,
):
    prop = SVProperty(
        name=f"test_property_{timestamp_str}",
    )
    create_property(session, prop)
    assert prop.id is not None
