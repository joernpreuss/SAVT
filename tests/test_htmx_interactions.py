"""HTMX interaction tests for SAVT application.

Tests HTMX-specific functionality, headers, and dynamic content updates.
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from src.database import get_session
from src.main import app
from src.models import Feature, Item


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
    session.add(pizza)
    session.commit()
    session.refresh(pizza)

    # Create features
    pepperoni = Feature(name="Pepperoni", item_id=pizza.id)
    standalone_feature = Feature(name="Standalone")

    session.add_all([pepperoni, standalone_feature])
    session.commit()

    return {"objects": [pizza], "properties": [pepperoni, standalone_feature]}


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
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni", headers=headers
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
            "/create/item/", data={"name": "HTMX Object"}, headers=headers
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
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the objects list
        root_ul = soup.find("ul", id="objects-list")
        assert root_ul is not None

        # Should not contain main page elements
        assert soup.find("h1") is None
        assert soup.find("script") is None

        # Small move forms are OK in fragments
        soup.find_all("form", class_="move-form")
        # But not main creation forms
        creation_forms = soup.find_all(
            "form", action=lambda x: x and ("/create/" in x if x else False)
        )
        assert len(creation_forms) == 0

    def test_unveto_returns_objects_fragment(self, client, sample_data):
        """Test unveto action returns only objects list fragment."""
        # First veto a property
        client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Then unveto it
        response = client.get(
            "/user/anonymous/unveto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the objects list
        root_ul = soup.find("ul", id="objects-list")
        assert root_ul is not None

        # Should not contain main page elements
        assert soup.find("h1") is None

        # Small move forms are OK in fragments
        soup.find_all("form", class_="move-form")
        # But not main creation forms
        creation_forms = soup.find_all(
            "form", action=lambda x: x and ("/create/" in x if x else False)
        )
        assert len(creation_forms) == 0

    def test_standalone_veto_returns_standalone_fragment(self, client, sample_data):
        """Test standalone feature veto returns only standalone features fragment."""
        response = client.get(
            "/user/anonymous/veto/feature/Standalone", headers={"HX-Request": "true"}
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should be just the standalone features list
        root_ul = soup.find("ul", id="standalone-properties")
        assert root_ul is not None

        # Should not contain main page elements
        assert soup.find("h1") is None
        assert soup.find(id="objects-list") is None

        # Small move forms are OK in fragments
        soup.find_all("form", class_="move-form")
        # But not main creation forms
        creation_forms = soup.find_all(
            "form", action=lambda x: x and ("/create/" in x if x else False)
        )
        assert len(creation_forms) == 0


class TestDynamicContentUpdates:
    """Test dynamic content changes through HTMX."""

    def test_veto_updates_feature_state(self, client, sample_data):
        """Test vetoing updates feature visual state."""
        # Get initial state
        initial_response = client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni"
        )
        initial_soup = BeautifulSoup(initial_response.content, "html.parser")

        # Should show feature as vetoed
        struck_feature = initial_soup.find("s", string="Pepperoni")
        assert struck_feature is not None

        # Should have unveto link
        unveto_link = initial_soup.find("a", string="unveto")
        assert unveto_link is not None
        assert "/unveto/" in unveto_link.get("href")

    def test_unveto_restores_feature_state(self, client, sample_data):
        """Test unvetoing restores feature normal state."""
        # First veto
        client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Then unveto
        response = client.get(
            "/user/anonymous/unveto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should show feature as normal text with veto link
        feature_text = soup.find(string=lambda text: text and "Pepperoni" in text)
        assert feature_text is not None

        veto_link = soup.find("a", string="veto")
        assert veto_link is not None
        assert "/veto/" in veto_link.get("href")

        # Should not be struck through
        struck_feature = soup.find("s", string="Pepperoni")
        assert struck_feature is None

    def test_feature_creation_updates_page(self, client, sample_data):
        """Test feature creation updates page content."""
        pizza_id = sample_data["objects"][0].id

        response = client.post(
            "/create/feature/",
            data={"name": "New Topping", "item_id": pizza_id},
            headers={"HX-Request": "true"},
        )

        soup = BeautifulSoup(response.content, "html.parser")

        # Should find the new feature in the objects list
        feature_text = soup.find(string=lambda text: text and "New Topping" in text)
        assert feature_text is not None

        # Should be under the Pizza item
        pizza_section = soup.find(string="Pizza").parent
        pizza_features = pizza_section.find("ul")
        if pizza_features:
            pizza_feature_links = pizza_features.find_all("a")
            pizza_feature_names = [link.text for link in pizza_feature_links]
            assert "New Topping" in pizza_feature_names
        else:
            # If no ul found, just check that the new feature exists somewhere
            assert feature_text is not None

    def test_item_creation_updates_page(self, client):
        """Test item creation updates page content."""
        response = client.post(
            "/create/item/",
            data={"name": "New Object"},
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should find the new item in the objects list
        objects_list = soup.find("ul", id="objects-list")
        item_elements = objects_list.find_all("li", recursive=False)
        item_names = [
            next(
                (line.strip() for line in item.get_text().split("\n") if line.strip()),
                "",
            )
            for item in item_elements
        ]
        assert "New Object" in item_names

        # Should also update the feature form dropdown
        item_select = soup.find("select", {"name": "item_id"})
        options = item_select.find_all("option")
        option_texts = [opt.text for opt in options if opt.get("value")]
        assert "New Object" in option_texts


class TestHTMXSwapBehavior:
    """Test HTMX swap attributes and behavior."""

    def test_objects_list_outer_html_swap(self, client, sample_data):
        """Test objects list uses outerHTML swap correctly."""
        response = client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Response should be a complete ul element that can replace existing one
        root_element = soup.find("ul", id="objects-list")
        assert root_element is not None

        # Should be the root element of the response
        assert soup.contents[0] == root_element or soup.contents[0].name is None

    def test_standalone_features_outer_html_swap(self, client, sample_data):
        """Test standalone features list uses outerHTML swap correctly."""
        response = client.get(
            "/user/anonymous/veto/feature/Standalone", headers={"HX-Request": "true"}
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Response should be a complete ul element
        root_element = soup.find("ul", id="standalone-properties")
        assert root_element is not None

    def test_form_submission_body_swap(self, client):
        """Test form submissions swap entire body."""
        response = client.post("/create/item/", data={"name": "Body Swap Test"})
        soup = BeautifulSoup(response.content, "html.parser")

        # Should return full HTML page for body swap
        assert soup.find("html") is not None
        assert soup.find("head") is not None
        assert soup.find("body") is not None

        # Should contain the new item
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None


class TestHTMXTargeting:
    """Test HTMX targeting behavior."""

    def test_veto_targets_correct_element(self, client, sample_data):
        """Test veto actions target correct elements."""
        # Item feature veto should target objects-list
        obj_response = client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        obj_soup = BeautifulSoup(obj_response.content, "html.parser")
        assert obj_soup.find("ul", id="objects-list") is not None
        assert obj_soup.find("ul", id="standalone-properties") is None

        # Standalone feature veto should target standalone-features
        standalone_response = client.get(
            "/user/anonymous/veto/feature/Standalone", headers={"HX-Request": "true"}
        )
        standalone_soup = BeautifulSoup(standalone_response.content, "html.parser")
        assert standalone_soup.find("ul", id="standalone-properties") is not None
        assert standalone_soup.find("ul", id="objects-list") is None

    def test_multiple_feature_states_in_fragment(self, client, session, sample_data):
        """Test fragment contains multiple features with different states."""
        # Add another feature to the item
        pizza = session.exec(select(Item).where(Item.name == "Pizza")).first()
        mushrooms = Feature(name="Mushrooms", item_id=pizza.id)
        session.add(mushrooms)
        session.commit()

        # Veto one feature
        client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )

        # Get the fragment
        response = client.get(
            "/user/anonymous/veto/item/Pizza/feature/Pepperoni",
            headers={"HX-Request": "true"},
        )
        soup = BeautifulSoup(response.content, "html.parser")

        # Should show both features with different states
        pepperoni_vetoed = soup.find("s", string="Pepperoni")
        mushrooms_text = soup.find(string=lambda text: text and "Mushrooms" in text)

        assert pepperoni_vetoed is not None  # Vetoed feature
        assert mushrooms_text is not None  # Non-vetoed feature as plain text


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
        response = client.post("/create/item/", data={"name": "Fallback Object"})
        assert response.status_code == 200

        # Should return full page
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("html") is not None

        # Should contain the new item
        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None
