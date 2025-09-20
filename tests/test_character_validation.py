"""
Test character validation in features and items.

Tests that:
1. Problematic characters (newlines, tabs, etc.) are rejected
2. Valid Unicode characters (umlauts, accents, etc.) are accepted
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.infrastructure.database.database import get_session
from src.main import app


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Test client for making HTTP requests."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_feature_character_validation(client: TestClient):
    """Test that feature creation rejects problematic characters but accepts Unicode."""
    # Test problematic characters - should fail
    problematic_names = [
        "test\nfeature",  # Newline
        "test\rfeature",  # Carriage return
        "test\tfeature",  # Tab
        "test\vfeature",  # Vertical tab
        "test\ffeature",  # Form feed
    ]

    for name in problematic_names:
        response = client.post(
            "/create/feature/", data={"name": name}, follow_redirects=False
        )
        # Should return error (400 or redirect with error)
        assert response.status_code in [400, 422, 302], (
            f"Should reject {repr(name)}, got status {response.status_code}"
        )

    # Test valid Unicode characters - should succeed
    valid_unicode_names = [
        "café",  # French
        "naïve",  # French
        "résumé",  # French
        "Müller",  # German umlaut
        "Björk",  # Swedish
        "José",  # Spanish
        "test feature",  # Space is OK
    ]

    for name in valid_unicode_names:
        response = client.post(
            "/create/feature/", data={"name": name}, follow_redirects=False
        )
        # Should succeed (200 or redirect)
        assert response.status_code in [200, 302, 303], (
            f"Should accept {repr(name)}, got status {response.status_code}"
        )


def test_item_character_validation(client: TestClient):
    """Test that item creation rejects problematic characters but accepts Unicode."""
    # Test problematic characters - should fail
    problematic_names = [
        "test\nitem",  # Newline
        "test\ritem",  # Carriage return
        "test\titem",  # Tab
    ]

    for name in problematic_names:
        response = client.post(
            "/create/item/", data={"name": name}, follow_redirects=False
        )
        # Should return error (400 or redirect with error)
        assert response.status_code in [400, 422, 302], (
            f"Should reject {repr(name)}, got status {response.status_code}"
        )

    # Test valid Unicode characters - should succeed
    valid_unicode_names = [
        "Café Menu",  # French with space
        "Müller's Pizza",  # German umlaut
        "José's Tacos",  # Spanish
    ]

    for name in valid_unicode_names:
        response = client.post(
            "/create/item/", data={"name": name}, follow_redirects=False
        )
        # Should succeed (200 or redirect)
        assert response.status_code in [200, 302, 303], (
            f"Should accept {repr(name)}, got status {response.status_code}"
        )
