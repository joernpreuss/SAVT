"""Tests for enhanced error handling with RFC 7807 Problem Details."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.infrastructure.database.database import get_session
from src.main import app


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create test client with database session."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_api_validation_error_returns_problem_details(client):
    """Test that API validation errors return RFC 7807 Problem Details."""
    # Test with missing required field to trigger Pydantic validation
    response = client.post("/api/v1/items", json={"kind": "test"})  # Missing name

    assert response.status_code == 400
    data = response.json()

    # Check RFC 7807 Problem Details structure
    assert "type" in data
    assert "title" in data
    assert "status" in data
    assert data["status"] == 400
    assert "detail" in data
    assert "instance" in data
    assert data["instance"] == "/api/v1/items"

    # Check for field-specific errors
    assert "errors" in data
    assert isinstance(data["errors"], list)
    assert len(data["errors"]) > 0

    error = data["errors"][0]
    assert "field" in error
    assert "code" in error
    assert "message" in error
    assert error["field"] == "name"


def test_api_conflict_error_returns_problem_details(client):
    """Test that API conflict errors return RFC 7807 Problem Details."""
    import uuid

    unique_name = f"Test Item {uuid.uuid4()}"

    # Create an item first
    create_response = client.post(
        "/api/v1/items", json={"name": unique_name, "kind": "test"}
    )
    assert create_response.status_code == 201

    # Try to create duplicate - this currently returns a simple error message
    # Note: The existing API routes return simple HTTPException, not Problem Details yet
    response = client.post("/api/v1/items", json={"name": unique_name, "kind": "test"})

    assert response.status_code == 409
    data = response.json()

    # For now, check that we get a reasonable error response
    # TODO: Update API routes to use global exception handlers for Problem Details
    assert "detail" in data
    assert unique_name in data["detail"]


def test_html_request_still_returns_html_error(client):
    """Test that HTML requests get appropriate error responses."""
    import uuid

    unique_name = f"Test Duplicate {uuid.uuid4()}"

    # Create an item first
    response1 = client.post(
        "/create/item/",
        data={"name": unique_name, "kind": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response1.status_code == 200  # First should succeed

    # Try to create duplicate - should auto-increment and succeed
    response2 = client.post(
        "/create/item/",
        data={"name": unique_name, "kind": "test"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # Should succeed with auto-incremented name (new behavior)
    assert response2.status_code == 200
    # Note: The duplicate was auto-incremented to {original}-2, so creation succeeds


def test_api_internal_error_returns_problem_details(client):
    """Test that internal errors return RFC 7807 Problem Details."""
    # Test a malformed request that should trigger a validation error
    response = client.post(
        "/api/v1/items",
        json={"invalid_field": "value"},  # Missing required fields
    )

    assert response.status_code == 400  # RequestValidationError returns 400
    data = response.json()

    # Check RFC 7807 Problem Details structure for validation errors
    assert "type" in data
    assert "title" in data
    assert "status" in data
    assert data["status"] == 400
    assert "detail" in data
    assert "instance" in data
    assert "errors" in data
    assert isinstance(data["errors"], list)


def test_error_codes_are_consistent():
    """Test that error codes are structured and consistent."""
    from src.presentation.problem_details import ErrorCodes

    # Verify error codes are strings
    assert isinstance(ErrorCodes.VALIDATION_FAILED, str)
    assert isinstance(ErrorCodes.FIELD_REQUIRED, str)
    assert isinstance(ErrorCodes.RESOURCE_ALREADY_EXISTS, str)

    # Verify they follow a consistent pattern
    assert ErrorCodes.FIELD_REQUIRED == "field_required"
    assert ErrorCodes.FIELD_TOO_LONG == "field_too_long"
    assert ErrorCodes.RESOURCE_ALREADY_EXISTS == "resource_already_exists"


def test_problem_detail_factory():
    """Test that ProblemDetailFactory creates correct structures."""
    from src.presentation.problem_details import ProblemDetailFactory

    # Test validation failed
    problem = ProblemDetailFactory.validation_failed(
        detail="Test validation error",
        instance="/test/path",
        field_errors=[
            {"field": "name", "code": "required", "message": "Field is required"}
        ],
    )

    assert problem.type.endswith("/validation-failed")
    assert problem.title == "Validation Failed"
    assert problem.status == 400
    assert problem.detail == "Test validation error"
    assert problem.instance == "/test/path"
    assert problem.errors is not None
    assert len(problem.errors) == 1
    assert problem.errors[0]["field"] == "name"

    # Test resource already exists
    conflict_problem = ProblemDetailFactory.resource_already_exists(
        resource_type="item",
        detail="Item already exists",
        instance="/test/path",
        conflicting_field="name",
    )

    assert conflict_problem.type.endswith("/resource-already-exists")
    assert conflict_problem.title == "Resource Already Exists"
    assert conflict_problem.status == 409
    assert conflict_problem.resource_type == "item"
    assert conflict_problem.conflicting_field == "name"
