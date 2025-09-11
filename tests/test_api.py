import json
import logging

import pytest
from fastapi.testclient import TestClient
from rich.console import Console
from rich.logging import RichHandler
from rich.syntax import Syntax
from sqlmodel import Session

from database import get_session
from main import app


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
    response = client.get(
        f"/api/user/test_user/create/property/test_prop_per_api_{timestamp_str}"
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

    response = client.get(f"/api/user/test_user_pro/create/property/{prop_name}")
    assert response.status_code == 200
    logging.info(f"create property status: {response.status_code}")
    _log_response_json("create property", response.json())
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra_1/veto/property/{prop_name}")
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra_2/veto/property/{prop_name}")
    assert response.status_code == 200
    logging.info(f"veto 2 status: {response.status_code}")
    _log_response_json("veto 2", response.json())
    # TODO check response content


def test_two_vetos_by_same_user(client: TestClient, timestamp_str: str):
    _setup_logging_once()
    prop_name = f"test_prop_controversial_same_{timestamp_str}"

    response = client.get(f"/api/user/test_user_pro/create/property/{prop_name}")
    assert response.status_code == 200
    logging.info(f"create property status: {response.status_code}")
    _log_response_json("create property", response.json())
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra/veto/property/{prop_name}")
    assert response.status_code == 200
    logging.info(f"veto 1 status: {response.status_code}")
    _log_response_json("veto 1", response.json())
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra/veto/property/{prop_name}")
    assert response.status_code == 200
    response_json = response.json()
    _log_response_json("veto 2 (same user)", response_json)
    assert len(response_json["vetoed"]["vetoed_by"]) == 1
