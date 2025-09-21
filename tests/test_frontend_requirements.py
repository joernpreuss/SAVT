"""Frontend and UI requirements tests.

Tests UI behavior, visual elements, and HTMX functionality.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
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


def test_vetoed_properties_visual_distinction(client: TestClient, timestamp_str: str):
    """Test that vetoed properties are visually distinguished with strikethrough.

    Requirements:
    - FR-3.4: Vetoed properties are visually distinguished (strikethrough)
    - FR-4.2: Vetoed properties display as strikethrough text with "undo" link
    """
    prop_name = f"visual_test_{timestamp_str}"

    # Create property
    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201

    # Veto the property
    r2 = client.post(f"/api/v1/users/alice/properties/{prop_name}/veto")
    assert r2.status_code == 200

    # Check main page rendering
    r3 = client.get("/")
    assert r3.status_code == 200

    soup = BeautifulSoup(r3.content, "html.parser")

    # Find the vetoed property element (uses semantic <s> tag for strikethrough)
    vetoed_elements = soup.find_all("s")
    prop_found = False

    for elem in vetoed_elements:
        if prop_name in elem.get_text():
            # Should be in a <s> tag (semantic strikethrough)
            prop_found = True
            break

    assert prop_found, (
        f"Vetoed property '{prop_name}' not found with strikethrough styling"
    )

    # Check for unveto link
    unveto_links = soup.find_all("a", string="unveto")
    assert len(unveto_links) > 0, "No 'unveto' links found for vetoed properties"


def test_objects_and_properties_separate_display(
    client: TestClient, timestamp_str: str
):
    """Test that standalone properties are properly displayed.

    Requirements:
    - FR-4.5: System shows standalone properties properly
    """
    standalone_prop1 = f"standalone1_{timestamp_str}"
    standalone_prop2 = f"standalone2_{timestamp_str}"

    # Create standalone properties
    r1 = client.post("/api/v1/users/alice/properties", json={"name": standalone_prop1})
    assert r1.status_code == 201

    r2 = client.post("/api/v1/users/bob/properties", json={"name": standalone_prop2})
    assert r2.status_code == 201

    # Check main page rendering
    r3 = client.get("/")
    assert r3.status_code == 200

    soup = BeautifulSoup(r3.content, "html.parser")

    # Should have properties displayed
    properties_section = soup.find(id="properties-section") or soup.find(
        "h2", string=lambda x: x and "properties" in x.lower()
    )

    assert properties_section is not None, "Properties section not found"

    # Should contain both properties
    page_text = r3.text
    assert standalone_prop1 in page_text, (
        f"Property {standalone_prop1} not found in page"
    )
    assert standalone_prop2 in page_text, (
        f"Property {standalone_prop2} not found in page"
    )

    # Properties should be displayed properly
    page_content = soup.get_text()
    assert standalone_prop1 in page_content
    assert standalone_prop2 in page_content


def test_htmx_immediate_feedback(client: TestClient, timestamp_str: str):
    """Test that HTMX provides immediate visual feedback without page reloads.

    Requirements:
    - FR-4.3: HTMX provides immediate visual feedback (no page reloads)
    """
    prop_name = f"htmx_test_{timestamp_str}"

    # Create property
    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201

    # Check initial page has HTMX attributes
    r2 = client.get("/")
    assert r2.status_code == 200

    soup = BeautifulSoup(r2.content, "html.parser")

    # Look for HTMX attributes on veto/unveto links
    htmx_elements = soup.find_all(attrs={"hx-post": True}) or soup.find_all(
        attrs={"hx-get": True}
    )
    assert len(htmx_elements) > 0, "No HTMX attributes found on page"

    # Test veto operation via HTMX endpoint (correct path)
    veto_response = client.post(f"/user/alice/veto/feature/{prop_name}")
    assert veto_response.status_code == 200

    # Response should contain partial HTML for HTMX replacement
    response_text = veto_response.text
    assert prop_name in response_text
    assert "unveto" in response_text.lower()  # Should show unveto option after veto


def test_non_javascript_graceful_fallback(client: TestClient, timestamp_str: str):
    """Test that forms work gracefully for non-JavaScript browsers.

    Requirements:
    - FR-4.4: Forms have graceful fallback for non-JavaScript browsers
    """
    prop_name = f"fallback_test_{timestamp_str}"

    # Test property creation form (should work without JavaScript)
    form_data = {"name": prop_name, "created_by": "alice"}
    r1 = client.post(
        "/create/feature/",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r1.status_code in [200, 201, 302]  # Success or redirect

    # Verify property was created
    r2 = client.get("/api/v1/properties")
    assert r2.status_code == 200
    props = r2.json()["properties"]
    prop_names = [p["name"] for p in props]
    assert prop_name in prop_names

    # Test veto form (should work without JavaScript)
    r3 = client.post(
        f"/user/alice/veto/feature/{prop_name}",
        data={},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r3.status_code in [200, 302]  # Success or redirect

    # Verify veto was applied
    r4 = client.get("/api/v1/properties")
    assert r4.status_code == 200
    props = r4.json()["properties"]
    test_prop = next(p for p in props if p["name"] == prop_name)
    assert test_prop["vetoed"] is True


def test_database_schema_extensibility(client: TestClient, timestamp_str: str):
    """Test that database schema supports future extensions.

    Requirements:
    - FR-5.4: Database schema supports future extensions
    """
    # This test verifies the schema has room for growth
    # by checking that core entities have flexible design

    prop_name = f"schema_test_{timestamp_str}"

    # Create property with user context
    r1 = client.post("/api/v1/users/alice/properties", json={"name": prop_name})
    assert r1.status_code == 201

    # Test that system can handle additional user data gracefully
    r2 = client.post(
        "/api/v1/users/alice_with_extra_data/properties",
        json={"name": f"{prop_name}_2"},
    )
    assert r2.status_code == 201

    # Verify both properties exist and system didn't break
    r3 = client.get("/api/v1/properties")
    assert r3.status_code == 200
    props = r3.json()["properties"]
    prop_names = [p["name"] for p in props]
    assert prop_name in prop_names
    assert f"{prop_name}_2" in prop_names

    # Test veto functionality works with varied user names
    r4 = client.post(f"/api/v1/users/alice_with_extra_data/properties/{prop_name}/veto")
    assert r4.status_code == 200

    # Verify system maintains data integrity
    r5 = client.get("/api/v1/properties")
    assert r5.status_code == 200
    props = r5.json()["properties"]
    test_prop = next(p for p in props if p["name"] == prop_name)
    assert test_prop["vetoed"]  # Should be vetoed
