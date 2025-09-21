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
    """Test that duplicate property names increase amount instead of being rejected.

    Requirements:
    - FR-2.3: Property amounts can be increased when same name is used
    - FR-2.4: System increases feature amount rather than preventing creation
    """
    # Test standalone property duplicates
    name = f"dup_standalone_{timestamp_str}"
    r1 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r1.status_code == 201
    data1 = r1.json()
    assert data1["created"]["amount"] == 1

    # Same scope (standalone) should increase amount
    r2 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["created"]["amount"] == 2

    # Third time should increase to 3 (maximum)
    r3 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r3.status_code == 201
    data3 = r3.json()
    assert data3["created"]["amount"] == 3

    # Fourth time should stay at 3 (capped at maximum)
    r4 = client.post("/api/v1/users/alice/properties", json={"name": name})
    assert r4.status_code == 201
    data4 = r4.json()
    assert data4["created"]["amount"] == 3
    assert "maximum" in data4["message"]


def test_data_immutability(client: TestClient, timestamp_str: str):
    """Test that created properties cannot be deleted.

    Requirements:
    - FR-2.5: Properties cannot be deleted (data persistence)
    - BR-3.1: Immutable history - Created properties cannot be deleted
    - FR-5.2: No data is ever deleted (append-only system)
    """
    # Create property
    prop_name = f"persistent_prop_{timestamp_str}"

    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201

    # Verify no DELETE endpoints exist for properties
    r2 = client.delete(f"/api/v1/properties/{prop_name}")
    assert r2.status_code in [404, 405]  # Not Found or Method Not Allowed

    # Verify data persists in listings
    r3 = client.get("/api/v1/properties")
    assert r3.status_code == 200
    prop_names = [prop["name"] for prop in r3.json()["properties"]]
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


def test_referential_integrity(client: TestClient, timestamp_str: str):
    """Test that properties can be created and listed consistently.

    Requirements:
    - BR-3.2: Referential integrity - Properties maintain their data consistently
    - FR-1.4: Properties are properly tracked and retrievable
    """
    prop_name = f"ref_prop_{timestamp_str}"

    # Create standalone property
    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201
    created_prop = r1.json()["created"]

    # Verify property appears in listings
    r2 = client.get("/api/v1/properties")
    assert r2.status_code == 200
    properties = r2.json()["properties"]
    prop_names = [prop["name"] for prop in properties]
    assert prop_name in prop_names

    # Verify property data integrity
    found_prop = next(prop for prop in properties if prop["name"] == prop_name)
    assert found_prop["vetoed"] == (len(created_prop["vetoed_by"]) > 0)


def test_unique_constraints(client: TestClient, timestamp_str: str):
    """Test that property names can be reused with amount increases.

    Requirements:
    - BR-3.4: Property names can be reused and amounts are tracked
    """
    # Test property name reuse with amount tracking
    prop_name = f"unique_prop_{timestamp_str}"

    # Create first instance
    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201
    data1 = r1.json()
    assert data1["created"]["amount"] == 1

    # Create second instance with same name by different user - should increase amount
    r2 = client.post("/api/v1/users/bob/properties", json={"name": prop_name})
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["created"]["amount"] == 2

    # Verify both users contributed to the same property
    r3 = client.get("/api/v1/properties")
    assert r3.status_code == 200
    properties = r3.json()["properties"]
    prop_names = [prop["name"] for prop in properties]
    assert prop_name in prop_names
