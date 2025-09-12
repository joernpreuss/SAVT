import pytest
from sqlmodel import Session

from src.models import SVObject, SVProperty
from src.service import (
    ObjectAlreadyExistsError,
    PropertyAlreadyExistsError,
    create_object,
    create_property,
    get_property,
    veto_object_property,
)


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


def test_create_object_conflict(session: Session, timestamp_str: str):
    name = f"obj_{timestamp_str}"
    create_object(session, SVObject(name=name))
    with pytest.raises(ObjectAlreadyExistsError):
        create_object(session, SVObject(name=name))


def test_create_property_conflict(session: Session, timestamp_str: str):
    name = f"prop_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    with pytest.raises(PropertyAlreadyExistsError):
        create_property(session, SVProperty(name=name))


def test_veto_idempotency(session: Session, timestamp_str: str):
    name = f"idem_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    p1 = veto_object_property(session, user="alice", name=name, veto=True)
    p2 = veto_object_property(session, user="alice", name=name, veto=True)
    assert p1 and p2
    assert p2.vetoed_by.count("alice") == 1


def test_unveto_idempotency(session: Session, timestamp_str: str):
    name = f"unidem_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    veto_object_property(session, user="alice", name=name, veto=True)
    p1 = veto_object_property(session, user="alice", name=name, veto=False)
    p2 = veto_object_property(session, user="alice", name=name, veto=False)
    assert p1 and p2
    assert "alice" not in p2.vetoed_by


def test_object_scoped_veto(session: Session, timestamp_str: str):
    obj = SVObject(name=f"o_{timestamp_str}")
    create_object(session, obj)

    # Create distinct property names (global uniqueness enforced by service)
    standalone = SVProperty(name=f"p_standalone_{timestamp_str}")
    for_object = SVProperty(name=f"p_for_object_{timestamp_str}", object_id=obj.id)
    create_property(session, standalone)
    create_property(session, for_object)

    # Veto only the object-scoped property
    veto_object_property(
        session, user="alice", name=for_object.name, object_name=obj.name, veto=True
    )

    s = get_property(session, name=standalone.name, obj_id=None)
    o = get_property(session, name=for_object.name, obj_id=obj.id)
    assert s and "alice" not in s.vetoed_by
    assert o and "alice" in o.vetoed_by
