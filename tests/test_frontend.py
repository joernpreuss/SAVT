"""Frontend tests for SAVT application.

Tests HTML rendering, template structure, and frontend functionality
without requiring JavaScript execution.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlmodel import Session

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
    salad = SVObject(name="Salad")
    session.add(pizza)
    session.add(salad)
    session.commit()
    session.refresh(pizza)
    session.refresh(salad)

    # Create properties
    pepperoni = SVProperty(name="Pepperoni", object_id=pizza.id)
    mushrooms = SVProperty(name="Mushrooms", object_id=pizza.id)
    croutons = SVProperty(name="Croutons", object_id=salad.id)
    standalone_prop = SVProperty(name="Standalone")

    session.add_all([pepperoni, mushrooms, croutons, standalone_prop])
    session.commit()

    return {
        "objects": [pizza, salad],
        "properties": [pepperoni, mushrooms, croutons, standalone_prop],
    }


class TestHTMLRendering:
    """Test HTML template rendering and structure."""

    def test_main_page_structure(self, client):
        """Test main page renders with correct HTML structure."""
        response = client.get("/")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, "html.parser")

        # Check basic HTML structure
        assert soup.find("title")
        assert soup.find("title").text == "Properties"
        assert soup.find("h1")
        assert soup.find("h1").text == "Suggestion And Veto Tool"

        # Check HTMX script is loaded
        htmx_script = soup.find("script", src="https://unpkg.com/htmx.org@1.9.12")
        assert htmx_script is not None

        # Check required CSS classes for HTMX
        style_tag = soup.find("style")
        assert style_tag is not None
        assert ".htmx-request" in style_tag.text
        assert ".fade-out" in style_tag.text

    def test_objects_list_rendering(self, client, sample_data):
        """Test objects and properties are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check objects list exists
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None

        # Check objects are rendered
        object_items = objects_list.find_all("li", recursive=False)
        assert len(object_items) >= 2  # Pizza and Salad

        # Check properties are nested under objects
        for obj_item in object_items:
            properties_list = obj_item.find("ul")
            if properties_list:
                property_items = properties_list.find_all("li")
                assert len(property_items) >= 0

    def test_standalone_properties_rendering(self, client, sample_data):
        """Test standalone properties are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check standalone properties list exists
        standalone_list = soup.find("ul", id="standalone-properties")
        assert standalone_list is not None

        # Check standalone properties are rendered
        property_items = standalone_list.find_all("li")
        assert len(property_items) >= 1  # At least the standalone property

    def test_forms_rendering(self, client):
        """Test create forms are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check object creation form
        object_form = soup.find("form", action="/create/object/")
        assert object_form is not None
        assert object_form.find("input", {"name": "name"}) is not None
        assert object_form.find("button", type="submit") is not None

        # Check property creation form
        property_form = soup.find("form", action="/create/property/")
        assert property_form is not None
        assert property_form.find("input", {"name": "name"}) is not None
        assert property_form.find("select", {"name": "object_id"}) is not None
        assert property_form.find("button", type="submit") is not None


class TestHTMXAttributes:
    """Test HTMX attributes are correctly set on elements."""

    def test_veto_links_have_htmx_attributes(self, client, sample_data):
        """Test veto links have correct HTMX attributes."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find veto links (non-vetoed properties)
        veto_links = soup.find_all("a", href=lambda x: x and "/veto/" in x)

        for link in veto_links:
            # Check HTMX attributes
            assert link.get("hx-get") is not None
            assert link.get("hx-target") is not None
            assert link.get("hx-swap") is not None

            # Verify fallback href matches hx-get
            assert link.get("href") == link.get("hx-get")

    def test_unveto_links_have_htmx_attributes(self, client, sample_data):
        """Test unveto links have correct HTMX attributes."""
        # First veto a property
        client.get("/user/anonymous/veto/property/Standalone")

        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find unveto links
        unveto_links = soup.find_all("a", href=lambda x: x and "/unveto/" in x)

        for link in unveto_links:
            # Check HTMX attributes
            assert link.get("hx-get") is not None
            assert link.get("hx-target") is not None
            assert link.get("hx-swap") is not None

            # Verify fallback href matches hx-get
            assert link.get("href") == link.get("hx-get")

    def test_forms_have_htmx_attributes(self, client):
        """Test forms have correct HTMX attributes."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check object creation form
        object_form = soup.find("form", action="/create/object/")
        assert object_form.get("hx-post") == "/create/object/"
        assert object_form.get("hx-target") == "body"
        assert object_form.get("hx-swap") == "outerHTML"

        # Check property creation form
        property_form = soup.find("form", action="/create/property/")
        assert property_form.get("hx-post") == "/create/property/"
        assert property_form.get("hx-target") == "body"
        assert property_form.get("hx-swap") == "outerHTML"


class TestVetoFunctionality:
    """Test veto/unveto functionality through HTML responses."""

    def test_veto_property_changes_display(self, client, sample_data):
        """Test vetoing a property changes its display."""
        # Get initial state
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find a property link that can be vetoed
        veto_link = soup.find("a", href=lambda x: x and "/veto/property/" in x)
        assert veto_link is not None

        property_name = veto_link.text
        veto_url = veto_link.get("href")

        # Veto the property
        veto_response = client.get(veto_url)
        assert veto_response.status_code == 200

        # Check the response contains vetoed property
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Property should now be struck through and have unveto link
        struck_property = veto_soup.find("s", string=property_name)
        assert struck_property is not None

        # Should have unveto link
        unveto_link = veto_soup.find("a", string="undo")
        assert unveto_link is not None
        assert "/unveto/" in unveto_link.get("href")

    def test_unveto_property_restores_display(self, client, sample_data):
        """Test unvetoing a property restores normal display."""
        # First veto a property
        veto_response = client.get("/user/anonymous/veto/property/Standalone")
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Find unveto link
        unveto_link = veto_soup.find("a", string="undo")
        assert unveto_link is not None
        unveto_url = unveto_link.get("href")

        # Unveto the property
        unveto_response = client.get(unveto_url)
        assert unveto_response.status_code == 200

        # Check property is no longer struck through
        unveto_soup = BeautifulSoup(unveto_response.content, "html.parser")

        # Property should be back to normal (clickable link)
        property_link = unveto_soup.find("a", string="Standalone")
        assert property_link is not None
        assert "/veto/" in property_link.get("href")


class TestFormSubmission:
    """Test form submissions work correctly."""

    def test_create_object_form_submission(self, client):
        """Test object creation form submission."""
        response = client.post("/create/object/", data={"name": "Test Object"}, follow_redirects=True)
        assert response.status_code == 200

        # Check new object appears in response
        soup = BeautifulSoup(response.content, "html.parser")
        objects_list = soup.find("ul", id="objects-list")

        # Should find the new object
        object_items = objects_list.find_all("li", recursive=False)
        object_names = [next((line.strip() for line in item.get_text().split("\n") if line.strip()), "") for item in object_items]
        assert "Test Object" in object_names

    def test_create_property_form_submission(self, client, sample_data):
        """Test property creation form submission."""
        # Get an object ID
        pizza_id = sample_data["objects"][0].id

        response = client.post(
            "/create/property/", data={"name": "Test Property", "object_id": pizza_id}
        )
        assert response.status_code == 200

        # Check new property appears under the object
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the property link
        property_link = soup.find("a", string="Test Property")
        assert property_link is not None

    def test_create_standalone_property(self, client):
        """Test creating a property without an object."""
        response = client.post(
            "/create/property/", data={"name": "New Standalone", "object_id": ""}
        )
        assert response.status_code == 200

        # Check new property appears in standalone section
        soup = BeautifulSoup(response.content, "html.parser")
        standalone_list = soup.find("ul", id="standalone-properties")

        property_link = standalone_list.find("a", string="New Standalone")
        assert property_link is not None


class TestHTMLValidation:
    """Test HTML structure and validation."""

    def test_html_has_required_ids(self, client):
        """Test HTML contains required IDs for HTMX targeting."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Required IDs for HTMX targets
        assert soup.find(id="objects-list") is not None
        assert soup.find(id="standalone-properties") is not None
        assert soup.find(id="obj_name") is not None
        assert soup.find(id="prop_name") is not None

    def test_property_ids_are_unique(self, client, sample_data):
        """Test each property has a unique ID."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all property elements with IDs
        property_elements = soup.find_all(id=lambda x: x and x.startswith("property-"))

        # Extract IDs
        property_ids = [elem.get("id") for elem in property_elements]

        # Check all IDs are unique
        assert len(property_ids) == len(set(property_ids))

    def test_accessibility_basics(self, client):
        """Test basic accessibility features."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check form inputs have proper attributes
        name_input = soup.find("input", {"name": "name"})
        assert name_input.get("required") is not None
        assert name_input.get("placeholder") is not None

        # Check buttons have proper text
        buttons = soup.find_all("button", type="submit")
        for button in buttons:
            assert button.text.strip() != ""


class TestFragmentRendering:
    """Test HTMX fragment templates render correctly."""

    def test_objects_list_fragment_structure(self, client, sample_data):
        """Test objects list fragment has correct structure."""
        # Trigger an action that returns the objects list fragment
        response = client.get("/user/anonymous/veto/object/Pizza/property/Pepperoni")
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the ul element with objects-list id
        root_element = soup.find("ul", id="objects-list")
        assert root_element is not None

    def test_standalone_properties_fragment_structure(self, client, sample_data):
        """Test standalone properties fragment has correct structure."""
        # Trigger an action that returns the standalone properties fragment
        response = client.get("/user/anonymous/veto/property/Standalone")
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the ul element with standalone-properties id
        root_element = soup.find("ul", id="standalone-properties")
        assert root_element is not None
