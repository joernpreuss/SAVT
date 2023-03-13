import json

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from main import app, get_session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_create_property(client: TestClient, timestamp_str: str):
    response = client.get(
        f"/api/user/test_user/create/property/test_prop_per_api_{timestamp_str}"
    )
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content


def test_two_vetos(client: TestClient, timestamp_str: str):
    prop_name = f"test_prop_controversial_two_{timestamp_str}"

    response = client.get(f"/api/user/test_user_pro/create/property/{prop_name}")
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra_1/veto/property/{prop_name}")
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra_2/veto/property/{prop_name}")
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content


def test_two_vetos_by_same_user(client: TestClient, timestamp_str: str):
    prop_name = f"test_prop_controversial_same_{timestamp_str}"

    response = client.get(f"/api/user/test_user_pro/create/property/{prop_name}")
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra/veto/property/{prop_name}")
    assert response.status_code == 200
    print(f"{response.json()=}")
    # TODO check response content

    response = client.get(f"/api/user/test_user_contra/veto/property/{prop_name}")
    assert response.status_code == 200
    response_json = response.json()
    print(f"{response_json=}")
    assert len(response_json["vetoed"]["vetoed_by"]) == 1
