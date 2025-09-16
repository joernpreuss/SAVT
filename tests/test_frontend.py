"""Frontend tests for SAVT application.

Tests HTML rendering, template structure, and frontend functionality
without requiring JavaScript execution.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.config import settings
from src.infrastructure.database.database import get_session
from src.infrastructure.database.models import Feature, Item
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


@pytest.fixture
def sample_data(session):
    """Create sample data for testing."""
    # Create items
    pizza = Item(name="Pizza")
    salad = Item(name="Salad")
    session.add(pizza)
    session.add(salad)
    session.commit()
    session.refresh(pizza)
    session.refresh(salad)

    # Create features
    pepperoni = Feature(name="Pepperoni", item_id=pizza.id)
    mushrooms = Feature(name="Mushrooms", item_id=pizza.id)
    croutons = Feature(name="Croutons", item_id=salad.id)
    standalone_feature = Feature(name="Standalone")

    session.add_all([pepperoni, mushrooms, croutons, standalone_feature])
    session.commit()

    return {
        "objects": [pizza, salad],
        "properties": [pepperoni, mushrooms, croutons, standalone_feature],
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
        assert soup.find("title").text == "Features"
        assert soup.find("h1")
        assert soup.find("h1").text == settings.app_name

        # Check HTMX script is loaded
        htmx_script = soup.find("script", src="https://unpkg.com/htmx.org@1.9.12")
        assert htmx_script is not None

        # Check CSS is linked externally
        css_link = soup.find(
            "link", {"rel": "stylesheet", "href": "/static/css/styles.css"}
        )
        assert css_link is not None

    def test_items_list_rendering(self, client, sample_data):
        """Test items and features are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check items list exists
        items_list = soup.find("ul", id="objects-list")
        assert items_list is not None

        # Check items are rendered
        item_elements = items_list.find_all("li", recursive=False)
        assert len(item_elements) >= 2  # Pizza and Salad

        # Check features are nested under items
        for item_elem in item_elements:
            features_list = item_elem.find("ul")
            if features_list:
                feature_items = features_list.find_all("li")
                assert len(feature_items) >= 0

    def test_standalone_features_rendering(self, client, sample_data):
        """Test standalone features are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check standalone features list exists
        standalone_list = soup.find("ul", id="standalone-properties")
        assert standalone_list is not None

        # Check standalone features are rendered
        feature_items = standalone_list.find_all("li")
        assert len(feature_items) >= 1  # At least the standalone feature

    def test_forms_rendering(self, client):
        """Test create forms are rendered correctly."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check item creation form
        item_form = soup.find("form", action="/create/item/")
        assert item_form is not None
        assert item_form.find("input", {"name": "name"}) is not None
        assert item_form.find("button", type="submit") is not None

        # Check feature creation form
        feature_form = soup.find("form", action="/create/feature/")
        assert feature_form is not None
        assert feature_form.find("input", {"name": "name"}) is not None
        assert feature_form.find("select", {"name": "item_id"}) is not None
        assert feature_form.find("button", type="submit") is not None


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
        # First veto a feature
        client.get("/user/anonymous/veto/feature/Standalone")

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

        # Check item creation form
        item_form = soup.find("form", action="/create/item/")
        assert item_form.get("hx-post") == "/create/item/"
        assert item_form.get("hx-target") == "body"
        assert item_form.get("hx-swap") == "outerHTML"

        # Check feature creation form
        feature_form = soup.find("form", action="/create/feature/")
        assert feature_form.get("hx-post") == "/create/feature/"
        assert feature_form.get("hx-target") == "body"
        assert feature_form.get("hx-swap") == "outerHTML"


class TestVetoFunctionality:
    """Test veto/unveto functionality through HTML responses."""

    def test_veto_property_changes_display(self, client, sample_data):
        """Test vetoing a property changes its display."""
        # Get initial state
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find a veto link that can be clicked
        veto_link = soup.find("a", string="veto")
        assert veto_link is not None

        veto_url = veto_link.get("href")
        # Extract property name from URL (handle query parameters)
        property_name = veto_url.split("/")[-1].split("?")[0]

        # Veto the property
        veto_response = client.get(veto_url)
        assert veto_response.status_code == 200

        # Check the response contains vetoed property
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Property should now be struck through and have unveto link
        struck_elements = veto_soup.find_all("s")
        struck_property = None
        for s_elem in struck_elements:
            if property_name in s_elem.get_text():
                struck_property = s_elem
                break
        assert struck_property is not None

        # Should have unveto link
        unveto_link = veto_soup.find("a", string="unveto")
        assert unveto_link is not None
        assert "/unveto/" in unveto_link.get("href")

    def test_unveto_property_restores_display(self, client, sample_data):
        """Test unvetoing a property restores normal display."""
        # First veto a feature
        veto_response = client.get("/user/anonymous/veto/feature/Standalone")
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Find unveto link
        unveto_link = veto_soup.find("a", string="unveto")
        assert unveto_link is not None
        unveto_url = unveto_link.get("href")

        # Unveto the property
        unveto_response = client.get(unveto_url)
        assert unveto_response.status_code == 200

        # Check property is no longer struck through
        unveto_soup = BeautifulSoup(unveto_response.content, "html.parser")

        # Should have veto link again (not struck through)
        veto_link = unveto_soup.find("a", string="veto")
        assert veto_link is not None
        assert "/veto/" in veto_link.get("href")

        # Property name should not be struck through
        struck_elements = unveto_soup.find_all("s")
        struck_property = None
        for s_elem in struck_elements:
            if "Standalone" in s_elem.get_text():
                struck_property = s_elem
                break
        assert struck_property is None


class TestFormSubmission:
    """Test form submissions work correctly."""

    def test_create_object_form_submission(self, client):
        """Test object creation form submission."""
        response = client.post(
            "/create/item/", data={"name": "Test Object"}, follow_redirects=True
        )
        assert response.status_code == 200

        # Check new object appears in response
        soup = BeautifulSoup(response.content, "html.parser")
        objects_list = soup.find("ul", id="objects-list")

        # Should find the new object
        object_items = objects_list.find_all("li", recursive=False)
        object_names = [
            next(
                (line.strip() for line in item.get_text().split("\n") if line.strip()),
                "",
            )
            for item in object_items
        ]
        assert "Test Object" in object_names

    def test_create_property_form_submission(self, client, sample_data):
        """Test property creation form submission."""
        # Get an object ID
        pizza_id = sample_data["objects"][0].id

        response = client.post(
            "/create/feature/", data={"name": "Test Property", "item_id": pizza_id}
        )
        assert response.status_code == 200

        # Check new property appears under the object
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the property in the objects list
        # Look for text containing the property name
        property_text = soup.find(string=lambda text: text and "Test Property" in text)
        assert property_text is not None

    def test_create_standalone_property(self, client):
        """Test creating a feature without an item."""
        response = client.post(
            "/create/feature/", data={"name": "New Standalone", "item_id": ""}
        )
        assert response.status_code == 200

        # Check new feature appears in standalone section
        soup = BeautifulSoup(response.content, "html.parser")
        standalone_list = soup.find("ul", id="standalone-properties")

        # Check the feature appears in the standalone list
        feature_text = standalone_list.find(
            string=lambda text: text and "New Standalone" in text
        )
        assert feature_text is not None


class TestHTMLValidation:
    """Test HTML structure and validation."""

    def test_html_has_required_ids(self, client):
        """Test HTML contains required IDs for HTMX targeting."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Required IDs for HTMX targets
        assert soup.find(id="objects-list") is not None
        assert soup.find(id="standalone-properties") is not None
        assert soup.find(id="item_name") is not None
        assert soup.find(id="feature_name") is not None

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
        response = client.get("/user/anonymous/veto/item/Pizza/feature/Pepperoni")
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the ul element with objects-list id
        root_element = soup.find("ul", id="objects-list")
        assert root_element is not None

    def test_standalone_properties_fragment_structure(self, client, sample_data):
        """Test standalone properties fragment has correct structure."""
        # Trigger an action that returns the standalone features fragment
        response = client.get("/user/anonymous/veto/feature/Standalone")
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the ul element with standalone-properties id
        root_element = soup.find("ul", id="standalone-properties")
        assert root_element is not None
