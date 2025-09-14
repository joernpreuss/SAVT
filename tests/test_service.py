import pytest
from sqlmodel import Session

from src.models import Feature, Item
from src.service import (
    ItemAlreadyExistsError,
    create_feature,
    create_item,
    get_feature,
    veto_item_feature,
)


def test_create_item_with_feature(
    session: Session,
    timestamp_str: str,
):
    """Test item and feature creation.

    Covers:
    - FR-1.1: Users can create items with unique names
    - FR-2.1: Users can create features with names
    - FR-2.2: Features can be associated with items
    """
    item = Item(
        name=f"test_item_{timestamp_str}",
    )
    create_item(session, item)
    assert item.id is not None

    feature = Feature(
        name=f"test_feature_{timestamp_str}",
        item_id=item.id,
    )
    create_feature(session, feature)
    assert feature.id is not None


def test_create_feature_without_item(
    session: Session,
    timestamp_str: str,
):
    """Test standalone feature creation.

    Covers:
    - FR-2.1: Users can create features with names
    - FR-2.2: Features can be standalone (not tied to items)
    """
    feature = Feature(
        name=f"test_feature_{timestamp_str}",
    )
    create_feature(session, feature)
    assert feature.id is not None


def test_create_item_conflict(session: Session, timestamp_str: str):
    """Test item name uniqueness enforcement.

    Covers:
    - FR-1.2: Item names must be unique within the system
    - FR-1.5: System prevents duplicate item creation (returns 409 error)
    """
    name = f"item_{timestamp_str}"
    create_item(session, Item(name=name))
    with pytest.raises(ItemAlreadyExistsError):
        create_item(session, Item(name=name))


def test_create_feature_conflict(session: Session, timestamp_str: str):
    """Test that duplicate feature names are now allowed.

    Covers:
    - Duplicate feature names are allowed for independent veto control
    """
    name = f"feature_{timestamp_str}"
    f1 = create_feature(session, Feature(name=name))
    f2 = create_feature(session, Feature(name=name))  # Should succeed now
    assert f1.id != f2.id  # Different IDs for same name


def test_veto_idempotency(session: Session, timestamp_str: str):
    """Test that multiple veto operations by same user are idempotent.

    Covers:
    - FR-3.2: Users can only veto once per feature (idempotent operation)
    - BR-3.3: Atomic operations - Veto/unveto operations are transactional
    """
    name = f"idem_{timestamp_str}"
    create_feature(session, Feature(name=name))
    f1 = veto_item_feature(session, user="alice", name=name, veto=True)
    f2 = veto_item_feature(session, user="alice", name=name, veto=True)
    assert f1 and f2
    assert f2.vetoed_by.count("alice") == 1


def test_unveto_idempotency(session: Session, timestamp_str: str):
    """Test that multiple unveto operations by same user are idempotent.

    Covers:
    - FR-3.3: Users can unveto their own vetoes
    - FR-3.6: Veto/unveto operations are immediate and persistent
    - BR-3.3: Atomic operations - Veto/unveto operations are transactional
    """
    name = f"unidem_{timestamp_str}"
    create_feature(session, Feature(name=name))
    veto_item_feature(session, user="alice", name=name, veto=True)
    f1 = veto_item_feature(session, user="alice", name=name, veto=False)
    f2 = veto_item_feature(session, user="alice", name=name, veto=False)
    assert f1 and f2
    assert "alice" not in f2.vetoed_by


def test_item_scoped_veto(session: Session, timestamp_str: str):
    """Test that vetoes are scoped correctly between standalone and item features.

    Covers:
    - FR-3.1: Any user can veto any feature
    - FR-3.5: System tracks which users vetoed each feature
    - FR-2.2: Features can be standalone or associated with items
    """
    item = Item(name=f"i_{timestamp_str}")
    create_item(session, item)

    # Create distinct feature names (global uniqueness enforced by service)
    standalone = Feature(name=f"f_standalone_{timestamp_str}")
    for_item = Feature(name=f"f_for_item_{timestamp_str}", item_id=item.id)
    create_feature(session, standalone)
    create_feature(session, for_item)

    # Veto only the item-scoped feature
    veto_item_feature(
        session, user="alice", name=for_item.name, item_name=item.name, veto=True
    )

    s = get_feature(session, name=standalone.name, item_id=None)
    i = get_feature(session, name=for_item.name, item_id=item.id)
    assert s and "alice" not in s.vetoed_by
    assert i and "alice" in i.vetoed_by
