import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax
from sqlmodel import Session

from src.infrastructure.database.database import get_session
from src.main import app


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


console = Console()


def _log_response_json(title: str, response_json: dict[str, Any] | list[Any]) -> None:
    pretty = json.dumps(response_json, indent=2, ensure_ascii=False)
    syntax = Syntax(pretty, "json", theme="monokai", word_wrap=False)
    console.rule(title)
    console.print(syntax)


def _setup_logging_once() -> None:
    if any(isinstance(h, RichHandler) for h in logging.getLogger().handlers):
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="%H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def test_create_feature(client: TestClient, timestamp_str: str):
    """Test feature creation via API endpoint.

    Requirements:
    - FR-2.1: Users can create properties with names
    """
    _setup_logging_once()
    response = client.post(
        "/api/v1/users/test_user/properties",
        json={"name": f"test_feature_per_api_{timestamp_str}"},
    )
    assert response.status_code == 201
    logging.info(f"create_feature status: {response.status_code}")
    data = response.json()
    _log_response_json("create_feature response", data)
    assert "created" in data
    assert data["created"]["name"].startswith("test_feature_per_api_")


def test_two_vetos(client: TestClient, timestamp_str: str):
    _setup_logging_once()
    feature_name = f"test_feature_controversial_two_{timestamp_str}"

    response = client.post(
        "/api/v1/users/test_user_pro/properties", json={"name": feature_name}
    )
    assert response.status_code == 201
    logging.info(f"create feature status: {response.status_code}")
    _log_response_json("create feature", response.json())
    # TODO check response content

    response = client.post(
        f"/api/v1/users/test_user_contra_1/properties/{feature_name}/veto"
    )
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.post(
        f"/api/v1/users/test_user_contra_2/properties/{feature_name}/veto"
    )
    assert response.status_code == 200
    logging.info(f"veto 2 status: {response.status_code}")
    _log_response_json("veto 2", response.json())
    # TODO check response content


def test_two_vetos_by_same_user(client: TestClient, timestamp_str: str):
    """Test that multiple veto attempts by same user are idempotent via API.

    Requirements:
    - FR-3.2: Users can only veto once per property (idempotent operation)
    """
    _setup_logging_once()
    feature_name = f"test_feature_controversial_same_{timestamp_str}"

    response = client.post(
        "/api/v1/users/test_user_pro/properties", json={"name": feature_name}
    )
    assert response.status_code == 201
    logging.info(f"create feature status: {response.status_code}")
    _log_response_json("create feature", response.json())
    # TODO check response content

    response = client.post(
        f"/api/v1/users/test_user_contra/properties/{feature_name}/veto"
    )
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.post(
        f"/api/v1/users/test_user_contra/properties/{feature_name}/veto"
    )
    assert response.status_code == 200
    response_json = response.json()
    _log_response_json("veto 2 (same user)", response_json)
    assert len(response_json["vetoed"]["vetoed_by"]) == 1


def test_create_feature_conflict(client: TestClient, timestamp_str: str):
    """Test that duplicate feature names are now allowed via API.

    Requirements:
    - FR-2.1: Users can create properties with names
    """
    name = f"dup_feature_{timestamp_str}"
    r1 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r1.status_code == 201
    r2 = client.post("/api/v1/users/bob/properties", json={"name": name})
    assert r2.status_code == 201  # Duplicates are now allowed


def test_veto_then_unveto_feature(client: TestClient, timestamp_str: str):
    """Test veto/unveto cycle via API.

    Requirements:
    - FR-3.1: Any user can veto any property
    - FR-3.3: Users can unveto their own vetoes
    - FR-3.5: System tracks which users vetoed each property
    - FR-3.6: Veto/unveto operations are immediate and persistent
    """
    name = f"veto_toggle_{timestamp_str}"
    r = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r.status_code == 201

    r = client.post(f"/api/v1/users/alice/properties/{name}/veto")
    assert r.status_code == 200
    assert "vetoed" in r.json()
    assert "vetoed_by" in r.json()["vetoed"]
    assert "alice" in r.json()["vetoed"]["vetoed_by"]

    r = client.post(f"/api/v1/users/alice/properties/{name}/unveto")
    assert r.status_code == 200
    assert "unvetoed" in r.json()
    assert "alice" not in r.json()["unvetoed"]["vetoed_by"]


def test_list_features_sorted_and_flags(client: TestClient, timestamp_str: str):
    names = [f"a_{timestamp_str}", f"b_{timestamp_str}", f"c_{timestamp_str}"]
    for n in names:
        assert (
            client.post("/api/v1/users/u/properties", json={"name": n}).status_code
            == 201
        )

    # Veto one to flip its flag
    assert client.post(f"/api/v1/users/u/properties/{names[1]}/veto").status_code == 200

    r = client.get("/api/v1/properties")
    assert r.status_code == 200
    body = r.json()
    assert "properties" in body
    features = body["properties"]
    # All requested names present
    returned_names = [f["name"] for f in features]
    for n in names:
        assert n in returned_names
    # Sorted by vetoed flag then name
    vetoed_flags = [f["vetoed"] for f in features]
    assert vetoed_flags.count(True) >= 1
    # All False entries appear before any True entries
    first_true_index = next(
        (i for i, v in enumerate(vetoed_flags) if v), len(vetoed_flags)
    )
    assert all(not v for v in vetoed_flags[:first_true_index])


def test_property_duplicate_prevention(client: TestClient, timestamp_str: str):
    """Test that duplicate property names within scope return proper error.

    Requirements:
    - FR-2.3: Property names must be unique within their scope (object or standalone)
    - FR-2.4: System prevents duplicate property creation (returns 409 error)
    """
    # Test standalone property duplicates
    name = f"dup_standalone_{timestamp_str}"
    r1 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r1.status_code == 201

    # Same scope (standalone) should conflict
    r2 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r2.status_code == 409

    # Test item-scoped property duplicates
    item_name = f"test_item_{timestamp_str}"
    r3 = client.post("/api/v1/users/alice/items", json={"name": item_name})
    assert r3.status_code == 201

    prop_name = f"scoped_prop_{timestamp_str}"
    r4 = client.post(
        f"/api/v1/users/alice/items/{item_name}/properties", json={"name": prop_name}
    )
    assert r4.status_code == 201

    # Same scope (item) should conflict
    r5 = client.post(
        f"/api/v1/users/alice/items/{item_name}/properties", json={"name": prop_name}
    )
    assert r5.status_code == 409


def test_data_immutability(client: TestClient, timestamp_str: str):
    """Test that created items and properties cannot be deleted.

    Requirements:
    - FR-1.3: Objects cannot be deleted (data persistence)
    - FR-2.5: Properties cannot be deleted (data persistence)
    - BR-3.1: Immutable history - Created items cannot be deleted
    - FR-5.2: No data is ever deleted (append-only system)
    """
    # Create item and property
    item_name = f"persistent_item_{timestamp_str}"
    prop_name = f"persistent_prop_{timestamp_str}"

    r1 = client.post("/api/v1/users/alice/items", json={"name": item_name})
    assert r1.status_code == 201

    r2 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r2.status_code == 201

    # Verify no DELETE endpoints exist for items/properties
    r3 = client.delete(f"/api/v1/items/{item_name}")
    assert r3.status_code == 405  # Method Not Allowed

    r4 = client.delete(f"/api/v1/properties/{prop_name}")
    assert r4.status_code == 405  # Method Not Allowed

    # Verify data persists in listings
    r5 = client.get("/api/v1/items")
    assert r5.status_code == 200
    item_names = [item["name"] for item in r5.json()["items"]]
    assert item_name in item_names

    r6 = client.get("/api/v1/properties")
    assert r6.status_code == 200
    prop_names = [prop["name"] for prop in r6.json()["properties"]]
    assert prop_name in prop_names


def test_database_persistence(client: TestClient, timestamp_str: str):
    """Test that all data persists in SQLite database.

    Requirements:
    - FR-5.1: All data persists in SQLite database
    - FR-5.3: System maintains complete audit trail of all actions
    """
    # Create and veto a property to generate audit trail
    prop_name = f"audit_prop_{timestamp_str}"

    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201

    r2 = client.post(f"/api/v1/users/alice/properties/{prop_name}/veto")
    assert r2.status_code == 200

    r3 = client.post(f"/api/v1/users/alice/properties/{prop_name}/unveto")
    assert r3.status_code == 200

    # Verify final state persists
    r4 = client.get("/api/v1/properties")
    assert r4.status_code == 200
    props = r4.json()["properties"]
    test_prop = next(p for p in props if p["name"] == prop_name)
    assert not test_prop["vetoed"]  # Should be unvetoed
    assert test_prop["vetoed_by"] == []  # No active vetoes


def test_referential_integrity(client: TestClient, timestamp_str: str):
    """Test that properties maintain references to objects.

    Requirements:
    - BR-3.2: Referential integrity - Properties maintain references to objects
    - FR-1.4: Objects display all their associated properties
    """
    item_name = f"ref_item_{timestamp_str}"
    prop_name = f"ref_prop_{timestamp_str}"

    # Create item
    r1 = client.post("/api/v1/users/alice/items", json={"name": item_name})
    assert r1.status_code == 201

    # Create property associated with item
    r2 = client.post(
        f"/api/v1/users/alice/items/{item_name}/properties", json={"name": prop_name}
    )
    assert r2.status_code == 201

    # Verify item shows its associated property
    r3 = client.get(f"/api/v1/items/{item_name}")
    assert r3.status_code == 200
    item_data = r3.json()
    assert "properties" in item_data
    prop_names = [p["name"] for p in item_data["properties"]]
    assert prop_name in prop_names

    # Verify property references correct item
    r4 = client.get("/api/v1/properties")
    assert r4.status_code == 200
    props = r4.json()["properties"]
    test_prop = next(p for p in props if p["name"] == prop_name)
    assert test_prop["item_name"] == item_name


def test_unique_constraints(client: TestClient, timestamp_str: str):
    """Test that unique constraints are enforced within scope.

    Requirements:
    - BR-3.4: Unique constraints - Names must be unique within scope
    """
    # Test item name uniqueness
    item_name = f"unique_item_{timestamp_str}"
    r1 = client.post("/api/v1/users/alice/items", json={"name": item_name})
    assert r1.status_code == 201

    r2 = client.post("/api/v1/users/bob/items", json={"name": item_name})
    assert r2.status_code == 409  # Conflict - item names must be globally unique

    # Test property scope uniqueness
    prop_name = f"scoped_unique_{timestamp_str}"

    # Same name in different scopes should be allowed
    r3 = client.post(
        "/api/v1/users/alice/properties", json={"name": prop_name}
    )  # Standalone
    assert r3.status_code == 201

    item2_name = f"scope_item_{timestamp_str}"
    r4 = client.post("/api/v1/users/alice/items", json={"name": item2_name})
    assert r4.status_code == 201

    r5 = client.post(
        f"/api/v1/users/alice/items/{item2_name}/properties", json={"name": prop_name}
    )  # Item-scoped
    assert r5.status_code == 201  # Different scope, should be allowed
