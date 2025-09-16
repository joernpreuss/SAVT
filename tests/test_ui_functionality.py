"""UI functionality tests for SAVT application.

Tests user interface behavior, form validation, and JavaScript-free functionality.
"""

from typing import TypedDict

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlmodel import Session

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


class PopulatedData(TypedDict):
    objects: list[Item]
    properties: list[Feature]


@pytest.fixture(name="populated_data")
def populated_data(session: Session) -> PopulatedData:
    """Create a populated dataset for testing."""
    # Create multiple items with features
    pizza = Item(name="Pizza")
    burger = Item(name="Burger")
    salad = Item(name="Salad")

    session.add_all([pizza, burger, salad])
    session.commit()
    session.refresh(pizza)
    session.refresh(burger)
    session.refresh(salad)

    # Create features for each item
    pizza_features = [
        Feature(name="Pepperoni", item_id=pizza.id),
        Feature(name="Mushrooms", item_id=pizza.id),
        Feature(name="Cheese", item_id=pizza.id),
    ]

    burger_features = [
        Feature(name="Beef", item_id=burger.id),
        Feature(name="Chicken", item_id=burger.id),
    ]

    salad_features = [
        Feature(name="Lettuce", item_id=salad.id),
        Feature(name="Tomatoes", item_id=salad.id),
    ]

    standalone_features = [
        Feature(name="Salt"),
        Feature(name="Pepper"),
        Feature(name="Oil"),
    ]

    all_features = (
        pizza_features + burger_features + salad_features + standalone_features
    )
    session.add_all(all_features)
    session.commit()

    return {"objects": [pizza, burger, salad], "properties": all_features}


class TestFormValidation:
    """Test form validation and error handling."""

    def test_empty_item_name_validation(self, client: TestClient):
        """Test creating item with empty name is handled properly."""
        # Try to create item with empty name
        response = client.post("/create/item/", data={"name": ""})

        # Should handle gracefully (either reject or show error)
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            # If accepted, check it doesn't create empty-named item
            soup = BeautifulSoup(response.content, "html.parser")
            objects_list = soup.find("ul", id="objects-list")
            # Should not find an empty item name
            empty_items = [
                li
                for li in objects_list.find_all("li", recursive=False)
                if li.get_text().strip() == ""
            ]
            assert len(empty_items) == 0

    def test_empty_feature_name_validation(
        self, client: TestClient, populated_data: PopulatedData
    ) -> None:
        """Test creating feature with empty name is handled properly."""
        pizza_id = populated_data["objects"][0].id

        response = client.post(
            "/create/feature/", data={"name": "", "item_id": pizza_id}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_duplicate_item_names(self, client):
        """Test creating items with duplicate names."""
        # Create first item
        response1 = client.post("/create/item/", data={"name": "Duplicate"})
        assert response1.status_code == 200

        # Try to create second item with same name
        response2 = client.post("/create/item/", data={"name": "Duplicate"})

        # Should handle gracefully (either allow or reject)
        assert response2.status_code in [200, 400, 409]

    def test_special_characters_in_names(self, client):
        """Test items and features with special characters."""
        special_names = [
            "Name with spaces",
            "Name-with-dashes",
            "Name_with_underscores",
            "Name'with'apostrophe",
            'Name"with"quotes',
            "Name/with/slashes",
        ]

        for name in special_names:
            response = client.post("/create/item/", data={"name": name})
            # Should either accept or reject gracefully
            assert response.status_code in [200, 400]

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                # If accepted, should find the item in the list
                objects_list = soup.find("ul", id="objects-list")
                assert objects_list is not None


class TestUserWorkflow:
    """Test complete user workflows and scenarios."""

    def test_complete_veto_workflow(self, client, populated_data):
        """Test complete workflow of vetoing and unvetoing features."""
        # Initial state - get the page
        initial_response = client.get("/")
        initial_soup = BeautifulSoup(initial_response.content, "html.parser")

        # Find a veto link to click
        veto_link = initial_soup.find("a", string="veto")
        assert veto_link is not None
        veto_url = veto_link.get("href")

        # Step 1: Veto the feature
        veto_response = client.get(veto_url)
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Verify feature is now vetoed
        struck_elements = veto_soup.find_all("s")
        vetoed_pepperoni = None
        for s_elem in struck_elements:
            if "Pepperoni" in s_elem.get_text():
                vetoed_pepperoni = s_elem
                break
        assert vetoed_pepperoni is not None

        # Find unveto link
        unveto_link = veto_soup.find("a", string="unveto")
        assert unveto_link is not None
        unveto_url = unveto_link.get("href")

        # Step 2: Unveto the feature
        unveto_response = client.get(unveto_url)
        unveto_soup = BeautifulSoup(unveto_response.content, "html.parser")

        # Verify feature is back to normal (not struck through)
        struck_elements = unveto_soup.find_all("s")
        normal_pepperoni = None
        for s_elem in struck_elements:
            if "Pepperoni" in s_elem.get_text():
                normal_pepperoni = s_elem
                break
        assert normal_pepperoni is None

        # Should have veto link available
        veto_link = unveto_soup.find("a", string="veto")
        assert veto_link is not None
        assert "/veto/" in veto_link.get("href")

    def test_multiple_vetos_workflow(self, client, populated_data):
        """Test workflow with multiple vetoed features."""
        # Veto multiple features
        features_to_veto = ["Pepperoni", "Beef", "Salt"]

        for feature_name in features_to_veto:
            if feature_name in ["Salt"]:  # Standalone feature
                veto_url = f"/user/anonymous/veto/feature/{feature_name}"
            elif feature_name == "Pepperoni":
                veto_url = f"/user/anonymous/veto/item/Pizza/feature/{feature_name}"
            elif feature_name == "Beef":
                veto_url = f"/user/anonymous/veto/item/Burger/feature/{feature_name}"

            response = client.get(veto_url)
            assert response.status_code == 200

        # Get final state and verify all are vetoed
        final_response = client.get("/")
        final_soup = BeautifulSoup(final_response.content, "html.parser")

        for feature_name in features_to_veto:
            struck_elements = final_soup.find_all("s")
            vetoed_feature = None
            for s_elem in struck_elements:
                if feature_name in s_elem.get_text():
                    vetoed_feature = s_elem
                    break
            assert vetoed_feature is not None, f"{feature_name} should be vetoed"

    def test_create_and_veto_workflow(self, client):
        """Test creating new items and immediately vetoing them."""
        # Create a new item
        item_response = client.post("/create/item/", data={"name": "New Item"})
        item_soup = BeautifulSoup(item_response.content, "html.parser")

        # Find the new item in select dropdown to get its ID
        item_select = item_soup.find("select", {"name": "item_id"})
        new_item_option = item_select.find("option", string="New Item")
        assert new_item_option is not None
        new_item_id = new_item_option.get("value")

        # Create a feature for the new item
        feature_response = client.post(
            "/create/feature/", data={"name": "New Feature", "item_id": new_item_id}
        )
        assert feature_response.status_code == 200

        # Veto the new feature
        veto_response = client.get(
            "/user/anonymous/veto/item/New Item/feature/New Feature"
        )
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Verify it's vetoed
        struck_elements = veto_soup.find_all("s")
        vetoed_feature = None
        for s_elem in struck_elements:
            if "New Feature" in s_elem.get_text():
                vetoed_feature = s_elem
                break
        assert vetoed_feature is not None


class TestUIAccessibility:
    """Test UI accessibility and usability features."""

    def test_focus_management(self, client):
        """Test that auto-focus is not applied to avoid page jumping."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check that no JavaScript auto-focuses on form elements
        script_tags = soup.find_all("script")
        focus_script = None
        for script in script_tags:
            if script.string and "focus()" in script.string:
                focus_script = script
                break

        # Should not have auto-focus to prevent page jumping
        assert focus_script is None

    def test_form_input_attributes(self, client):
        """Test form inputs have proper attributes for accessibility."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check input attributes (name inputs now have auto-generated defaults)
        name_inputs = soup.find_all("input", {"name": "name"})
        for input_elem in name_inputs:
            # Item name input is now optional (auto-generated Pizza-1, Pizza-2, etc.)
            if input_elem.get("id") == "item_name":
                assert input_elem.get("required") is None  # Not required anymore
                assert "Pizza-1, Pizza-2" in input_elem.get("placeholder")
            else:
                # Feature name inputs should still be required
                assert input_elem.get("required") is not None
            assert input_elem.get("placeholder") is not None
            assert input_elem.get("id") is not None

    def test_link_accessibility(self, client, populated_data):
        """Test links have proper accessibility features."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # All interactive links should have meaningful text
        links = soup.find_all("a")
        for link in links:
            link_text = link.get_text().strip()
            # Links should have non-empty text
            assert link_text != ""
            # Should have href
            assert link.get("href") is not None


class TestUIConsistency:
    """Test UI consistency across different states."""

    def test_consistent_feature_display(self, client, populated_data):
        """Test features display consistently across items."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        objects_list = soup.find("ul", id="objects-list")
        item_elements = objects_list.find_all("li", recursive=False)

        for item_elem in item_elements:
            feature_list = item_elem.find("ul")
            if feature_list:
                feature_items = feature_list.find_all("li")
                for feature_item in feature_items:
                    # Each feature should have either a link or struck text
                    feature_link = feature_item.find("a")
                    struck_text = feature_item.find("s")

                    # Should have one or the other, not both for the feature name
                    assert (feature_link is not None) != (struck_text is not None)

    def test_consistent_standalone_feature_display(self, client, populated_data):
        """Test standalone features display consistently."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        standalone_list = soup.find("ul", id="standalone-properties")
        feature_items = standalone_list.find_all("li")

        for feature_item in feature_items:
            # Each feature should have either a link or struck text
            feature_link = feature_item.find("a")
            struck_text = feature_item.find("s")

            # Should have one or the other for the feature name
            assert (feature_link is not None) != (struck_text is not None)

    def test_form_state_preservation(self, client, populated_data):
        """Test form state is preserved after operations."""
        # Submit a form and check if form fields are properly reset/preserved
        response = client.post("/create/item/", data={"name": "Test Item"})
        soup = BeautifulSoup(response.content, "html.parser")

        # Item name field should be present and functional
        item_name_input = soup.find("input", {"name": "name", "id": "item_name"})
        assert item_name_input is not None

        # Feature form should include the new item in dropdown
        item_select = soup.find("select", {"name": "item_id"})
        options = item_select.find_all("option")
        option_texts = [opt.text for opt in options if opt.get("value")]
        assert "Test Item" in option_texts


class TestErrorHandling:
    """Test error handling in the UI."""

    def test_invalid_veto_urls(self, client):
        """Test handling of invalid veto URLs."""
        invalid_urls = [
            "/user/anonymous/veto/item/NonExistent/feature/AlsoNonExistent",
            "/user/anonymous/veto/feature/DoesNotExist",
            "/user/anonymous/unveto/item/Fake/feature/Fake",
        ]

        for url in invalid_urls:
            response = client.get(url)
            # Should handle gracefully, not crash
            assert response.status_code in [200, 404, 400]

    def test_malformed_form_data(self, client):
        """Test handling of malformed form submissions."""
        # Missing required fields
        response1 = client.post("/create/item/", data={})
        assert response1.status_code in [200, 400, 422]

        # Invalid item_id
        response2 = client.post(
            "/create/feature/",
            data={"name": "Test Feature", "item_id": "invalid_id"},
        )
        assert response2.status_code in [200, 400, 422]

    def test_very_long_names(self, client):
        """Test that very long names are rejected with appropriate error."""
        long_name = "x" * 150  # Name longer than 100 character limit

        response = client.post("/create/item/", data={"name": long_name})
        # Should reject with 400 Bad Request
        assert response.status_code == 400


class TestBrowserCompatibility:
    """Test features work without JavaScript (graceful degradation)."""

    def test_no_javascript_functionality(self, client, populated_data):
        """Test core functionality works without JavaScript."""
        # All veto/unveto operations should work via href fallbacks
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Find and click a veto link using href (not hx-get)
        veto_link = soup.find("a", href=lambda x: x and "/veto/" in x)
        if veto_link:
            href = veto_link.get("href")
            veto_response = client.get(href)
            assert veto_response.status_code == 200

    def test_form_submission_without_htmx(self, client):
        """Test forms work with standard submission."""
        # Submit form using standard POST (not HTMX)
        response = client.post("/create/item/", data={"name": "Standard Form"})
        assert response.status_code == 200

        # Should return full page with the new item
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("html") is not None

        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None
