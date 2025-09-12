import json
import logging

import pytest
from fastapi.testclient import TestClient
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax
from sqlmodel import Session

from src.database import get_session
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


def _log_response_json(title: str, response_json: dict | list) -> None:
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


def test_create_property(client: TestClient, timestamp_str: str):
    _setup_logging_once()
    response = client.post(
        "/api/users/test_user/properties",
        json={"name": f"test_prop_per_api_{timestamp_str}"},
    )
    assert response.status_code == 200
    logging.info(f"create_property status: {response.status_code}")
    data = response.json()
    _log_response_json("create_property response", data)
    assert "created" in data
    assert data["created"]["name"].startswith("test_prop_per_api_")


def test_two_vetos(client: TestClient, timestamp_str: str):
    _setup_logging_once()
    prop_name = f"test_prop_controversial_two_{timestamp_str}"

    response = client.post(
        "/api/users/test_user_pro/properties", json={"name": prop_name}
    )
    assert response.status_code == 200
    logging.info(f"create property status: {response.status_code}")
    _log_response_json("create property", response.json())
    # TODO check response content

    response = client.post(f"/api/users/test_user_contra_1/properties/{prop_name}/veto")
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.post(f"/api/users/test_user_contra_2/properties/{prop_name}/veto")
    assert response.status_code == 200
    logging.info(f"veto 2 status: {response.status_code}")
    _log_response_json("veto 2", response.json())
    # TODO check response content


def test_two_vetos_by_same_user(client: TestClient, timestamp_str: str):
    _setup_logging_once()
    prop_name = f"test_prop_controversial_same_{timestamp_str}"

    response = client.post(
        "/api/users/test_user_pro/properties", json={"name": prop_name}
    )
    assert response.status_code == 200
    logging.info(f"create property status: {response.status_code}")
    _log_response_json("create property", response.json())
    # TODO check response content

    response = client.post(f"/api/users/test_user_contra/properties/{prop_name}/veto")
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.post(f"/api/users/test_user_contra/properties/{prop_name}/veto")
    assert response.status_code == 200
    response_json = response.json()
    _log_response_json("veto 2 (same user)", response_json)
    assert len(response_json["vetoed"]["vetoed_by"]) == 1


def test_create_property_conflict(client: TestClient, timestamp_str: str):
    name = f"dup_prop_{timestamp_str}"
    r1 = client.post("/api/users/alice/properties", json={"name": name})
    assert r1.status_code == 200
    r2 = client.post("/api/users/bob/properties", json={"name": name})
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"].lower()


def test_veto_then_unveto_property(client: TestClient, timestamp_str: str):
    name = f"veto_toggle_{timestamp_str}"
    r = client.post("/api/users/alice/properties", json={"name": name})
    assert r.status_code == 200

    r = client.post(f"/api/users/alice/properties/{name}/veto")
    assert r.status_code == 200
    assert "vetoed" in r.json()
    assert "vetoed_by" in r.json()["vetoed"]
    assert "alice" in r.json()["vetoed"]["vetoed_by"]

    r = client.post(f"/api/users/alice/properties/{name}/unveto")
    assert r.status_code == 200
    assert "unvetoed" in r.json()
    assert "alice" not in r.json()["unvetoed"]["vetoed_by"]


def test_list_properties_sorted_and_flags(client: TestClient, timestamp_str: str):
    names = [f"a_{timestamp_str}", f"b_{timestamp_str}", f"c_{timestamp_str}"]
    for n in names:
        assert (
            client.post("/api/users/u/properties", json={"name": n}).status_code == 200
        )

    # Veto one to flip its flag
    assert client.post(f"/api/users/u/properties/{names[1]}/veto").status_code == 200

    r = client.get("/api/properties")
    assert r.status_code == 200
    body = r.json()
    assert "properties" in body
    props = body["properties"]
    # All requested names present
    returned_names = [p["name"] for p in props]
    for n in names:
        assert n in returned_names
    # Sorted by vetoed flag then name
    vetoed_flags = [p["vetoed"] for p in props]
    assert vetoed_flags.count(True) >= 1
    # All False entries appear before any True entries
    first_true_index = next(
        (i for i, v in enumerate(vetoed_flags) if v), len(vetoed_flags)
    )
    assert all(not v for v in vetoed_flags[:first_true_index])
