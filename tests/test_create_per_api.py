from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_create_property_without_user():
    response = client.get("/create/propery/test_prop_per_api")
    assert response.status_code == 200


def test_create_property_with_user():
    response = client.get("/user/test_user/create/propery/test_prop_per_api")
    assert response.status_code == 200


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()
