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


# Item API Endpoint Tests


def test_create_item(client: TestClient, timestamp_str: str):
    """Test item creation via API endpoint.

    Requirements:
    - FR-1.1: Users can create objects with unique names
    - FR-1.2: Object names must be unique within the system
    """
    _setup_logging_once()
    item_name = f"test_item_{timestamp_str}"
    response = client.post(
        "/api/v1/items",
        json={"name": item_name, "kind": "test"},
    )
    assert response.status_code == 201
    logging.info(f"create_item status: {response.status_code}")
    data = response.json()
    _log_response_json("create_item response", data)
    assert "created" in data
    assert data["created"]["name"] == item_name
    assert data["created"]["kind"] == "test"
    assert data["created"]["features"] == []
    assert data["message"] == "Item created successfully"


def test_create_item_with_user(client: TestClient, timestamp_str: str):
    """Test item creation with user attribution via API.

    Requirements:
    - FR-1.1: Users can create objects with unique names
    - User attribution tracking
    """
    _setup_logging_once()
    item_name = f"user_item_{timestamp_str}"
    response = client.post(
        "/api/v1/users/alice/items",
        json={"name": item_name, "kind": "user_test"},
    )
    assert response.status_code == 201
    data = response.json()
    _log_response_json("create_item_with_user response", data)
    assert data["created"]["name"] == item_name
    assert data["created"]["created_by"] == "alice"
    assert data["created"]["kind"] == "user_test"


def test_create_item_duplicate_conflict(client: TestClient, timestamp_str: str):
    """Test that duplicate item names are rejected via API.

    Requirements:
    - FR-1.2: Object names must be unique within the system
    - FR-1.5: System prevents duplicate object creation (returns 409 error)
    """
    _setup_logging_once()
    item_name = f"duplicate_item_{timestamp_str}"

    # Create first item
    r1 = client.post("/api/v1/items", json={"name": item_name})
    assert r1.status_code == 201
    logging.info(f"First item creation status: {r1.status_code}")

    # Attempt to create duplicate
    r2 = client.post("/api/v1/items", json={"name": item_name})
    assert r2.status_code == 409
    logging.info(f"Duplicate item creation status: {r2.status_code}")
    error_data = r2.json()
    _log_response_json("duplicate_item_error", error_data)
    assert "already exists" in error_data["detail"]


def test_list_items_empty(client: TestClient):
    """Test listing items when none exist.

    Requirements:
    - FR-1.4: Objects display all their associated properties
    """
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_items_with_data(client: TestClient, timestamp_str: str):
    """Test listing items with feature counts.

    Requirements:
    - FR-1.4: Objects display all their associated properties
    - Feature counting and sorting
    """
    _setup_logging_once()

    # Create test items
    item1_name = f"list_item_1_{timestamp_str}"
    item2_name = f"list_item_2_{timestamp_str}"

    r1 = client.post("/api/v1/items", json={"name": item1_name, "kind": "type1"})
    assert r1.status_code == 201

    r2 = client.post("/api/v1/items", json={"name": item2_name, "kind": "type2"})
    assert r2.status_code == 201

    # List items
    response = client.get("/api/v1/items")
    assert response.status_code == 200
    data = response.json()
    _log_response_json("list_items response", data)

    assert "items" in data
    items = data["items"]

    # Find our test items
    test_items = [item for item in items if item["name"] in [item1_name, item2_name]]
    assert len(test_items) == 2

    # Verify structure
    for item in test_items:
        assert "id" in item
        assert "name" in item
        assert "kind" in item
        assert "feature_count" in item
        assert "vetoed_feature_count" in item
        assert item["feature_count"] == 0  # No features added yet


def test_get_item_by_name(client: TestClient, timestamp_str: str):
    """Test retrieving specific item by name.

    Requirements:
    - FR-1.4: Objects display all their associated properties
    - Detailed item information retrieval
    """
    _setup_logging_once()
    item_name = f"get_item_{timestamp_str}"

    # Create item
    r1 = client.post(
        "/api/v1/users/bob/items", json={"name": item_name, "kind": "detailed"}
    )
    assert r1.status_code == 201

    # Get item details
    response = client.get(f"/api/v1/items/{item_name}")
    assert response.status_code == 200
    data = response.json()
    _log_response_json("get_item response", data)

    assert data["name"] == item_name
    assert data["kind"] == "detailed"
    assert data["created_by"] == "bob"
    assert isinstance(data["features"], list)
    assert len(data["features"]) == 0  # No features added yet


def test_get_item_not_found(client: TestClient, timestamp_str: str):
    """Test retrieving non-existent item.

    Requirements:
    - Proper 404 error handling
    """
    non_existent_name = f"non_existent_{timestamp_str}"
    response = client.get(f"/api/v1/items/{non_existent_name}")
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"]


def test_delete_item(client: TestClient, timestamp_str: str):
    """Test soft deleting an item.

    Requirements:
    - FR-1.3: Objects cannot be deleted (data persistence)
    - BR-3.1: Immutable history - Created items cannot be deleted (soft delete only)
    - Soft delete functionality
    """
    _setup_logging_once()
    item_name = f"delete_item_{timestamp_str}"

    # Create item
    r1 = client.post("/api/v1/items", json={"name": item_name})
    assert r1.status_code == 201

    # Delete item
    response = client.delete(f"/api/v1/items/{item_name}")
    assert response.status_code == 200
    data = response.json()
    _log_response_json("delete_item response", data)

    assert data["success"] is True
    assert "deleted successfully" in data["message"]
    assert data["item_name"] == item_name

    # Verify item no longer appears in listings
    r3 = client.get("/api/v1/items")
    assert r3.status_code == 200
    items = r3.json()["items"]
    item_names = [item["name"] for item in items]
    assert item_name not in item_names

    # Verify item no longer accessible by name
    r4 = client.get(f"/api/v1/items/{item_name}")
    assert r4.status_code == 404


def test_delete_item_not_found(client: TestClient, timestamp_str: str):
    """Test deleting non-existent item.

    Requirements:
    - Proper 404 error handling for delete operations
    """
    non_existent_name = f"delete_non_existent_{timestamp_str}"
    response = client.delete(f"/api/v1/items/{non_existent_name}")
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"]


def test_restore_item(client: TestClient, timestamp_str: str):
    """Test restoring a soft-deleted item.

    Requirements:
    - Data recovery functionality
    - Reversible soft delete operations
    """
    _setup_logging_once()
    item_name = f"restore_item_{timestamp_str}"

    # Create and delete item
    r1 = client.post("/api/v1/items", json={"name": item_name, "kind": "restorable"})
    assert r1.status_code == 201

    r2 = client.delete(f"/api/v1/items/{item_name}")
    assert r2.status_code == 200

    # Restore item
    response = client.post(f"/api/v1/items/{item_name}/restore")
    assert response.status_code == 200
    data = response.json()
    _log_response_json("restore_item response", data)

    assert data["success"] is True
    assert "restored successfully" in data["message"]
    assert data["item_name"] == item_name

    # Verify item reappears in listings
    r4 = client.get("/api/v1/items")
    assert r4.status_code == 200
    items = r4.json()["items"]
    item_names = [item["name"] for item in items]
    assert item_name in item_names

    # Verify item accessible by name again
    r5 = client.get(f"/api/v1/items/{item_name}")
    assert r5.status_code == 200
    assert r5.json()["name"] == item_name
    assert r5.json()["kind"] == "restorable"


def test_restore_item_not_found(client: TestClient, timestamp_str: str):
    """Test restoring non-existent deleted item.

    Requirements:
    - Proper 404 error handling for restore operations
    """
    non_existent_name = f"restore_non_existent_{timestamp_str}"
    response = client.post(f"/api/v1/items/{non_existent_name}/restore")
    assert response.status_code == 404
    error_data = response.json()
    assert "not found" in error_data["detail"]


def test_item_feature_relationship(client: TestClient, timestamp_str: str):
    """Test item-feature relationship through API.

    Requirements:
    - FR-1.4: Objects display all their associated properties
    - FR-2.2: Properties can be standalone or associated with objects
    - Feature-item associations
    """
    _setup_logging_once()
    item_name = f"feature_item_{timestamp_str}"
    feature_name = f"item_feature_{timestamp_str}"

    # Create item first
    r1 = client.post("/api/v1/items", json={"name": item_name, "kind": "featured"})
    assert r1.status_code == 201

    # Create standalone feature
    r2 = client.post("/api/v1/properties", json={"name": feature_name})
    assert r2.status_code == 201

    # Get item details to verify no features initially
    r3 = client.get(f"/api/v1/items/{item_name}")
    assert r3.status_code == 200
    data = r3.json()
    _log_response_json("item_before_features", data)
    assert len(data["features"]) == 0

    # Verify item appears in listing with correct feature count
    r4 = client.get("/api/v1/items")
    assert r4.status_code == 200
    items = r4.json()["items"]
    test_item = next(item for item in items if item["name"] == item_name)
    assert test_item["feature_count"] == 0
    assert test_item["vetoed_feature_count"] == 0


def test_item_data_immutability(client: TestClient, timestamp_str: str):
    """Test that created items follow immutability principles.

    Requirements:
    - FR-1.3: Objects cannot be deleted (data persistence)
    - BR-3.1: Immutable history - Created items cannot be deleted
    - FR-5.2: No data is ever deleted (append-only system)
    - FR-5.3: System maintains complete audit trail of all actions
    """
    _setup_logging_once()
    item_name = f"immutable_item_{timestamp_str}"

    # Create item
    r1 = client.post(
        "/api/v1/users/alice/items", json={"name": item_name, "kind": "permanent"}
    )
    assert r1.status_code == 201
    original_data = r1.json()["created"]

    # Verify item data persists
    r2 = client.get(f"/api/v1/items/{item_name}")
    assert r2.status_code == 200
    current_data = r2.json()

    # Core data should remain unchanged
    assert current_data["name"] == original_data["name"]
    assert current_data["kind"] == original_data["kind"]
    assert current_data["created_by"] == original_data["created_by"]
    assert current_data["id"] == original_data["id"]

    # Soft delete and verify data still accessible for audit
    r3 = client.delete(f"/api/v1/items/{item_name}")
    assert r3.status_code == 200

    # After soft delete, item shouldn't appear in normal listings
    r4 = client.get("/api/v1/items")
    assert r4.status_code == 200
    active_items = [item["name"] for item in r4.json()["items"]]
    assert item_name not in active_items

    # But can be restored (proving data wasn't destroyed)
    r5 = client.post(f"/api/v1/items/{item_name}/restore")
    assert r5.status_code == 200

    # After restore, data should be exactly the same
    r6 = client.get(f"/api/v1/items/{item_name}")
    assert r6.status_code == 200
    restored_data = r6.json()
    assert restored_data["name"] == original_data["name"]
    assert restored_data["kind"] == original_data["kind"]
    assert restored_data["created_by"] == original_data["created_by"]


def test_item_api_comprehensive_workflow(client: TestClient, timestamp_str: str):
    """Test complete item management workflow via API.

    Requirements:
    - Complete item lifecycle management
    - Integration between all item endpoints
    """
    _setup_logging_once()

    # Create multiple items with different users and types
    items_data: list[dict[str, str | None]] = [
        {
            "name": f"workflow_item_1_{timestamp_str}",
            "kind": "priority",
            "user": "alice",
        },
        {"name": f"workflow_item_2_{timestamp_str}", "kind": "normal", "user": "bob"},
        {"name": f"workflow_item_3_{timestamp_str}", "kind": None, "user": None},
    ]

    created_items = []

    # Create items
    for item_data in items_data:
        if item_data["user"]:
            response = client.post(
                f"/api/v1/users/{item_data['user']}/items",
                json={"name": item_data["name"], "kind": item_data["kind"]},
            )
        else:
            response = client.post(
                "/api/v1/items",
                json={"name": item_data["name"], "kind": item_data["kind"]},
            )
        assert response.status_code == 201
        created_items.append(response.json()["created"])

    # Verify all items in listing
    r1 = client.get("/api/v1/items")
    assert r1.status_code == 200
    all_items = r1.json()["items"]
    created_names = [item["name"] for item in created_items]
    listed_names = [item["name"] for item in all_items]

    for name in created_names:
        assert name in listed_names

    # Get individual item details
    for item_data in items_data:
        response = client.get(f"/api/v1/items/{item_data['name']}")
        assert response.status_code == 200
        details = response.json()
        assert details["name"] == item_data["name"]
        assert details["kind"] == item_data["kind"]
        assert details["created_by"] == item_data["user"]

    # Delete one item
    delete_target = items_data[0]["name"]
    r2 = client.delete(f"/api/v1/items/{delete_target}")
    assert r2.status_code == 200

    # Verify it's removed from listings
    r3 = client.get("/api/v1/items")
    assert r3.status_code == 200
    remaining_items = [item["name"] for item in r3.json()["items"]]
    assert delete_target not in remaining_items

    # Restore deleted item
    r4 = client.post(f"/api/v1/items/{delete_target}/restore")
    assert r4.status_code == 200

    # Verify it's back in listings
    r5 = client.get("/api/v1/items")
    assert r5.status_code == 200
    final_items = [item["name"] for item in r5.json()["items"]]
    assert delete_target in final_items

    _log_response_json("workflow_final_state", {"total_items": len(final_items)})
