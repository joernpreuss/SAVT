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
    """Test object and property creation.

    Covers:
    - FR-1.1: Users can create objects with unique names
    - FR-2.1: Users can create properties with names
    - FR-2.2: Properties can be associated with objects
    """
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
    """Test standalone property creation.

    Covers:
    - FR-2.1: Users can create properties with names
    - FR-2.2: Properties can be standalone (not tied to objects)
    """
    prop = SVProperty(
        name=f"test_property_{timestamp_str}",
    )
    create_property(session, prop)
    assert prop.id is not None


def test_create_object_conflict(session: Session, timestamp_str: str):
    """Test object name uniqueness enforcement.

    Covers:
    - FR-1.2: Object names must be unique within the system
    - FR-1.5: System prevents duplicate object creation (returns 409 error)
    """
    name = f"obj_{timestamp_str}"
    create_object(session, SVObject(name=name))
    with pytest.raises(ObjectAlreadyExistsError):
        create_object(session, SVObject(name=name))


def test_create_property_conflict(session: Session, timestamp_str: str):
    """Test property name uniqueness enforcement.

    Covers:
    - FR-2.3: Property names must be unique within their scope
    - FR-2.4: System prevents duplicate property creation (returns 409 error)
    """
    name = f"prop_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    with pytest.raises(PropertyAlreadyExistsError):
        create_property(session, SVProperty(name=name))


def test_veto_idempotency(session: Session, timestamp_str: str):
    """Test that multiple veto operations by same user are idempotent.

    Covers:
    - FR-3.2: Users can only veto once per property (idempotent operation)
    - BR-3.3: Atomic operations - Veto/unveto operations are transactional
    """
    name = f"idem_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    p1 = veto_object_property(session, user="alice", name=name, veto=True)
    p2 = veto_object_property(session, user="alice", name=name, veto=True)
    assert p1 and p2
    assert p2.vetoed_by.count("alice") == 1


def test_unveto_idempotency(session: Session, timestamp_str: str):
    """Test that multiple unveto operations by same user are idempotent.

    Covers:
    - FR-3.3: Users can unveto their own vetoes
    - FR-3.6: Veto/unveto operations are immediate and persistent
    - BR-3.3: Atomic operations - Veto/unveto operations are transactional
    """
    name = f"unidem_{timestamp_str}"
    create_property(session, SVProperty(name=name))
    veto_object_property(session, user="alice", name=name, veto=True)
    p1 = veto_object_property(session, user="alice", name=name, veto=False)
    p2 = veto_object_property(session, user="alice", name=name, veto=False)
    assert p1 and p2
    assert "alice" not in p2.vetoed_by


def test_object_scoped_veto(session: Session, timestamp_str: str):
    """Test that vetoes are scoped correctly between standalone and object properties.

    Covers:
    - FR-3.1: Any user can veto any property
    - FR-3.5: System tracks which users vetoed each property
    - FR-2.2: Properties can be standalone or associated with objects
    """
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
