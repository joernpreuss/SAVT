"""HTMX interaction tests for SAVT application.

Tests HTMX-specific functionality, headers, and dynamic content updates.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.database import get_session
from src.main import app
from src.models import SVObject, SVProperty


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Test client for making HTTP requests."""

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_data(session):
    """Create sample data for testing."""
    # Create objects
    pizza = SVObject(name="Pizza")
    session.add(pizza)
    session.commit()
    session.refresh(pizza)

    # Create properties
    pepperoni = SVProperty(name="Pepperoni", object_id=pizza.id)
    standalone_prop = SVProperty(name="Standalone")

    session.add_all([pepperoni, standalone_prop])
    session.commit()

    return {"objects": [pizza], "properties": [pepperoni, standalone_prop]}


class TestHTMXHeaders:
    """Test HTMX request/response headers."""

    def test_htmx_request_header_detection(self, client):
        """Test server detects HTMX requests correctly."""
        # Regular request
        response = client.get("/")
        assert response.status_code == 200

        # HTMX request
        htmx_response = client.get("/", headers={"HX-Request": "true"})
        assert htmx_response.status_code == 200

        # Both should work but might return different content
        assert response.content != b"" and htmx_response.content != b""

    def test_veto_with_htmx_headers(self, client, sample_data):
        """Test veto requests with HTMX headers."""
        headers = {
            "HX-Request": "true",
            "HX-Target": "objects-list",
            "HX-Current-URL": "http://testserver/",
        }

        response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni", headers=headers
        )
        assert response.status_code == 200

        # Should return fragment, not full page
        soup = BeautifulSoup(response.content, "html.parser")

        # Should not have full HTML structure
        assert soup.find("html") is None
        assert soup.find("head") is None

        # Should have the targeted fragment
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None

    def test_form_submission_with_htmx_headers(self, client):
        """Test form submissions with HTMX headers."""
        headers = {"HX-Request": "true", "HX-Target": "body"}

        response = client.post(
            "/create/object/", data={"name": "HTMX Object"}, headers=headers
        )
        assert response.status_code == 200

        # Should return full page content for body target
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("html") is not None


class TestPartialUpdates:
    """Test HTMX partial content updates."""

    def test_veto_returns_objects_fragment(self, client, sample_data):
        """Test veto action returns only objects list fragment."""
        response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the objects list
        root_ul = soup.find("ul", id="objects-list")
        assert root_ul is not None

        # Should not contain other page elements
        assert soup.find("h1") is None
        assert soup.find("form") is None
        assert soup.find("script") is None

    def test_unveto_returns_objects_fragment(self, client, sample_data):
        """Test unveto action returns only objects list fragment."""
        # First veto a property
        client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Then unveto it
        response = client.get(
            "/user/anonymous/unveto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the objects list
        root_ul = soup.find("ul", id="objects-list")
        assert root_ul is not None

        # Should not contain other page elements
        assert soup.find("h1") is None
        assert soup.find("form") is None

    def test_standalone_veto_returns_standalone_fragment(self, client, sample_data):
        """Test standalone property veto returns only standalone properties fragment."""
        response = client.get(
            "/user/anonymous/veto/property/Standalone", headers={"HX-Request": "true"}
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the standalone properties list
        root_ul = soup.find("ul", id="standalone-properties")
        assert root_ul is not None

        # Should not contain other page elements
        assert soup.find("h1") is None
        assert soup.find("form") is None
        assert soup.find(id="objects-list") is None


class TestDynamicContentUpdates:
    """Test dynamic content changes through HTMX."""

    def test_veto_updates_property_state(self, client, sample_data):
        """Test vetoing updates property visual state."""
        # Get initial state
        initial_response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni"
        )
        initial_soup = BeautifulSoup(initial_response.content, "html.parser")

        # Should show property as vetoed
        struck_property = initial_soup.find("s", string="Pepperoni")
        assert struck_property is not None

        # Should have unveto link
        unveto_link = initial_soup.find("a", string="undo")
        assert unveto_link is not None
        assert "/unveto/" in unveto_link.get("href")

    def test_unveto_restores_property_state(self, client, sample_data):
        """Test unvetoing restores property normal state."""
        # First veto
        client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Then unveto
        response = client.get(
            "/user/anonymous/unveto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should show property as normal (not struck through)
        property_link = soup.find("a", string="Pepperoni")
        assert property_link is not None
        assert "/veto/" in property_link.get("href")

        # Should not be struck through
        struck_property = soup.find("s", string="Pepperoni")
        assert struck_property is None

    def test_property_creation_updates_page(self, client, sample_data):
        """Test property creation updates page content."""
        pizza_id = sample_data["objects"][0].id

        response = client.post(
            "/create/property/",
            data={"name": "New Topping", "object_id": pizza_id},
            headers={"HX-Request": "true"},
        )

        soup = BeautifulSoup(response.content, "html.parser")

        # Should find the new property in the objects list
        new_property_link = soup.find("a", string="New Topping")
        assert new_property_link is not None

        # Should be under the Pizza object
        pizza_section = soup.find(string="Pizza").parent
        pizza_properties = pizza_section.find("ul")
        if pizza_properties:
            pizza_property_links = pizza_properties.find_all("a")
            pizza_property_names = [link.text for link in pizza_property_links]
            assert "New Topping" in pizza_property_names
        else:
            # If no ul found, just check that the new property exists somewhere
            assert new_property_link is not None

    def test_object_creation_updates_page(self, client):
        """Test object creation updates page content."""
        response = client.post(
            "/create/object/",
            data={"name": "New Object"},
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should find the new object in the objects list
        objects_list = soup.find("ul", id="objects-list")
        object_items = objects_list.find_all("li", recursive=False)
        object_names = [
            next(
                (line.strip() for line in item.get_text().split("\n") if line.strip()),
                "",
            )
            for item in object_items
        ]
        assert "New Object" in object_names

        # Should also update the property form dropdown
        object_select = soup.find("select", {"name": "object_id"})
        options = object_select.find_all("option")
        option_texts = [opt.text for opt in options if opt.get("value")]
        assert "New Object" in option_texts


class TestHTMXSwapBehavior:
    """Test HTMX swap attributes and behavior."""

    def test_objects_list_outer_html_swap(self, client, sample_data):
        """Test objects list uses outerHTML swap correctly."""
        response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Response should be a complete ul element that can replace existing one
        root_element = soup.find("ul", id="objects-list")
        assert root_element is not None

        # Should be the root element of the response
        assert soup.contents[0] == root_element or soup.contents[0].name is None

    def test_standalone_properties_outer_html_swap(self, client, sample_data):
        """Test standalone properties list uses outerHTML swap correctly."""
        response = client.get(
            "/user/anonymous/veto/property/Standalone", headers={"HX-Request": "true"}
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Response should be a complete ul element
        root_element = soup.find("ul", id="standalone-properties")
        assert root_element is not None

    def test_form_submission_body_swap(self, client):
        """Test form submissions swap entire body."""
        response = client.post("/create/object/", data={"name": "Body Swap Test"})
        soup = BeautifulSoup(response.content, "html.parser")

        # Should return full HTML page for body swap
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None

        # Should contain the new object
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None


class TestHTMXTargeting:
    """Test HTMX targeting behavior."""

    def test_veto_targets_correct_element(self, client, sample_data):
        """Test veto actions target correct elements."""
        # Object property veto should target objects-list
        obj_response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        obj_soup = BeautifulSoup(obj_response.content, "html.parser")
        assert obj_soup.find("ul", id="objects-list") is not None
        assert obj_soup.find("ul", id="standalone-properties") is None

        # Standalone property veto should target standalone-properties
        standalone_response = client.get(
            "/user/anonymous/veto/property/Standalone", headers={"HX-Request": "true"}
        )
        standalone_soup = BeautifulSoup(standalone_response.content, "html.parser")
        assert standalone_soup.find("ul", id="standalone-properties") is not None
        assert standalone_soup.find("ul", id="objects-list") is None

    def test_multiple_property_states_in_fragment(self, client, session, sample_data):
        """Test fragment contains multiple properties with different states."""
        # Add another property to the object
        pizza = session.exec(select(SVObject).where(SVObject.name == "Pizza")).first()
        mushrooms = SVProperty(name="Mushrooms", object_id=pizza.id)
        session.add(mushrooms)
        session.commit()

        # Veto one property
        client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Get the fragment
        response = client.get(
            "/user/anonymous/veto/object/Pizza/property/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should show both properties with different states
        pepperoni_vetoed = soup.find("s", string="Pepperoni")
        mushrooms_link = soup.find("a", string="Mushrooms")

        assert pepperoni_vetoed is not None  # Vetoed property
        assert mushrooms_link is not None  # Non-vetoed property


class TestHTMXFallbackBehavior:
    """Test HTMX graceful degradation and fallbacks."""

    def test_veto_links_have_fallback_href(self, client, sample_data):
        """Test veto links work without HTMX (graceful degradation)."""
        # Get page without HTMX headers
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find veto links
        veto_links = soup.find_all("a", href=lambda x: x and "/veto/" in x)

        for link in veto_links:
            href = link.get("href")
            hx_get = link.get("hx-get")

            # Fallback href should match HTMX hx-get
            assert href == hx_get

            # Link should work without HTMX
            fallback_response = client.get(href)
            assert fallback_response.status_code == 200

    def test_forms_work_without_htmx(self, client):
        """Test forms work without HTMX headers."""
        # Submit form without HTMX headers
        response = client.post("/create/object/", data={"name": "Fallback Object"})
        assert response.status_code == 200

        # Should return full page
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("html") is not None

        # Should contain the new object
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None
