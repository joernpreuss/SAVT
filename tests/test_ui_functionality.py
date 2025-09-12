"""UI functionality tests for SAVT application.

Tests user interface behavior, form validation, and JavaScript-free functionality.
"""

from typing import TypedDict

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


class PopulatedData(TypedDict):
    objects: list[SVObject]
    properties: list[SVProperty]


@pytest.fixture(name="populated_data")
def populated_data(session: Session) -> PopulatedData:
    """Create a populated dataset for testing."""
    # Create multiple objects with properties
    pizza = SVObject(name="Pizza")
    burger = SVObject(name="Burger")
    salad = SVObject(name="Salad")

    session.add_all([pizza, burger, salad])
    session.commit()
    session.refresh(pizza)
    session.refresh(burger)
    session.refresh(salad)

    # Create properties for each object
    pizza_props = [
        SVProperty(name="Pepperoni", object_id=pizza.id),
        SVProperty(name="Mushrooms", object_id=pizza.id),
        SVProperty(name="Cheese", object_id=pizza.id),
    ]

    burger_props = [
        SVProperty(name="Beef", object_id=burger.id),
        SVProperty(name="Chicken", object_id=burger.id),
    ]

    salad_props = [
        SVProperty(name="Lettuce", object_id=salad.id),
        SVProperty(name="Tomatoes", object_id=salad.id),
    ]

    standalone_props = [
        SVProperty(name="Salt"),
        SVProperty(name="Pepper"),
        SVProperty(name="Oil"),
    ]

    all_props = pizza_props + burger_props + salad_props + standalone_props
    session.add_all(all_props)
    session.commit()

    return {"objects": [pizza, burger, salad], "properties": all_props}


class TestFormValidation:
    """Test form validation and error handling."""

    def test_empty_object_name_validation(self, client: TestClient):
        """Test creating object with empty name is handled properly."""
        # Try to create object with empty name
        response = client.post("/create/object/", data={"name": ""})

        # Should handle gracefully (either reject or show error)
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            # If accepted, check it doesn't create empty-named object
            soup = BeautifulSoup(response.content, "html.parser")
            objects_list = soup.find("ul", id="objects-list")
            # Should not find an empty object name
            empty_objects = [
                li
                for li in objects_list.find_all("li", recursive=False)
                if li.get_text().strip() == ""
            ]
            assert len(empty_objects) == 0

    def test_empty_property_name_validation(self, client: TestClient, populated_data: PopulatedData) -> None:
        """Test creating property with empty name is handled properly."""
        pizza_id = populated_data["objects"][0].id

        response = client.post(
            "/create/property/", data={"name": "", "object_id": pizza_id}
        )

        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_duplicate_object_names(self, client):
        """Test creating objects with duplicate names."""
        # Create first object
        response1 = client.post("/create/object/", data={"name": "Duplicate"})
        assert response1.status_code == 200

        # Try to create second object with same name
        response2 = client.post("/create/object/", data={"name": "Duplicate"})

        # Should handle gracefully (either allow or reject)
        assert response2.status_code in [200, 400, 409]

    def test_special_characters_in_names(self, client):
        """Test objects and properties with special characters."""
        special_names = [
            "Name with spaces",
            "Name-with-dashes",
            "Name_with_underscores",
            "Name'with'apostrophe",
            'Name"with"quotes',
            "Name/with/slashes",
        ]

        for name in special_names:
            response = client.post("/create/object/", data={"name": name})
            # Should either accept or reject gracefully
            assert response.status_code in [200, 400]

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")
                # If accepted, should find the object in the list
                objects_list = soup.find("ul", id="objects-list")
                assert objects_list is not None


class TestUserWorkflow:
    """Test complete user workflows and scenarios."""

    def test_complete_veto_workflow(self, client, populated_data):
        """Test complete workflow of vetoing and unvetoing properties."""
        # Initial state - get the page
        initial_response = client.get("/")
        initial_soup = BeautifulSoup(initial_response.content, "html.parser")

        # Find a property to veto
        pepperoni_link = initial_soup.find("a", string="Pepperoni")
        assert pepperoni_link is not None
        veto_url = pepperoni_link.get("href")

        # Step 1: Veto the property
        veto_response = client.get(veto_url)
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Verify property is now vetoed
        vetoed_pepperoni = veto_soup.find("s", string="Pepperoni")
        assert vetoed_pepperoni is not None

        # Find unveto link
        unveto_link = veto_soup.find("a", string="undo")
        assert unveto_link is not None
        unveto_url = unveto_link.get("href")

        # Step 2: Unveto the property
        unveto_response = client.get(unveto_url)
        unveto_soup = BeautifulSoup(unveto_response.content, "html.parser")

        # Verify property is back to normal
        normal_pepperoni = unveto_soup.find("a", string="Pepperoni")
        assert normal_pepperoni is not None
        assert "/veto/" in normal_pepperoni.get("href")

    def test_multiple_vetos_workflow(self, client, populated_data):
        """Test workflow with multiple vetoed properties."""
        # Veto multiple properties
        properties_to_veto = ["Pepperoni", "Beef", "Salt"]

        for prop_name in properties_to_veto:
            if prop_name in ["Salt"]:  # Standalone property
                veto_url = f"/user/anonymous/veto/property/{prop_name}"
            elif prop_name == "Pepperoni":
                veto_url = f"/user/anonymous/veto/object/Pizza/property/{prop_name}"
            elif prop_name == "Beef":
                veto_url = f"/user/anonymous/veto/object/Burger/property/{prop_name}"

            response = client.get(veto_url)
            assert response.status_code == 200

        # Get final state and verify all are vetoed
        final_response = client.get("/")
        final_soup = BeautifulSoup(final_response.content, "html.parser")

        for prop_name in properties_to_veto:
            vetoed_prop = final_soup.find("s", string=prop_name)
            assert vetoed_prop is not None, f"{prop_name} should be vetoed"

    def test_create_and_veto_workflow(self, client):
        """Test creating new items and immediately vetoing them."""
        # Create a new object
        obj_response = client.post("/create/object/", data={"name": "New Object"})
        obj_soup = BeautifulSoup(obj_response.content, "html.parser")

        # Find the new object in select dropdown to get its ID
        object_select = obj_soup.find("select", {"name": "object_id"})
        new_obj_option = object_select.find("option", string="New Object")
        assert new_obj_option is not None
        new_obj_id = new_obj_option.get("value")

        # Create a property for the new object
        prop_response = client.post(
            "/create/property/", data={"name": "New Property", "object_id": new_obj_id}
        )
        assert prop_response.status_code == 200

        # Veto the new property
        veto_response = client.get(
            "/user/anonymous/veto/object/New Object/property/New Property"
        )
        veto_soup = BeautifulSoup(veto_response.content, "html.parser")

        # Verify it's vetoed
        vetoed_prop = veto_soup.find("s", string="New Property")
        assert vetoed_prop is not None


class TestUIAccessibility:
    """Test UI accessibility and usability features."""

    def test_focus_management(self, client):
        """Test focus is set correctly on form elements."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check that JavaScript sets focus to property name input
        script_tags = soup.find_all("script")
        focus_script = None
        for script in script_tags:
            if script.string and "focus()" in script.string:
                focus_script = script
                break

        assert focus_script is not None
        assert "prop_name" in focus_script.string

    def test_form_input_attributes(self, client):
        """Test form inputs have proper attributes for accessibility."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        # Check required attributes
        name_inputs = soup.find_all("input", {"name": "name"})
        for input_elem in name_inputs:
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

    def test_consistent_property_display(self, client, populated_data):
        """Test properties display consistently across objects."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        objects_list = soup.find("ul", id="objects-list")
        object_items = objects_list.find_all("li", recursive=False)

        for obj_item in object_items:
            property_list = obj_item.find("ul")
            if property_list:
                property_items = property_list.find_all("li")
                for prop_item in property_items:
                    # Each property should have either a link (non-vetoed) or struck text (vetoed)
                    prop_link = prop_item.find("a")
                    struck_text = prop_item.find("s")

                    # Should have one or the other, not both for the property name
                    assert (prop_link is not None) != (struck_text is not None)

    def test_consistent_standalone_property_display(self, client, populated_data):
        """Test standalone properties display consistently."""
        response = client.get("/")
        soup = BeautifulSoup(response.content, "html.parser")

        standalone_list = soup.find("ul", id="standalone-properties")
        property_items = standalone_list.find_all("li")

        for prop_item in property_items:
            # Each property should have either a link or struck text
            prop_link = prop_item.find("a")
            struck_text = prop_item.find("s")

            # Should have one or the other for the property name
            assert (prop_link is not None) != (struck_text is not None)

    def test_form_state_preservation(self, client, populated_data):
        """Test form state is preserved after operations."""
        # Submit a form and check if form fields are properly reset/preserved
        response = client.post("/create/object/", data={"name": "Test Object"})
        soup = BeautifulSoup(response.content, "html.parser")

        # Object name field should be present and functional
        obj_name_input = soup.find("input", {"name": "name", "id": "obj_name"})
        assert obj_name_input is not None

        # Property form should include the new object in dropdown
        object_select = soup.find("select", {"name": "object_id"})
        options = object_select.find_all("option")
        option_texts = [opt.text for opt in options if opt.get("value")]
        assert "Test Object" in option_texts


class TestErrorHandling:
    """Test error handling in the UI."""

    def test_invalid_veto_urls(self, client):
        """Test handling of invalid veto URLs."""
        invalid_urls = [
            "/user/anonymous/veto/object/NonExistent/property/AlsoNonExistent",
            "/user/anonymous/veto/property/DoesNotExist",
            "/user/anonymous/unveto/object/Fake/property/Fake",
        ]

        for url in invalid_urls:
            response = client.get(url)
            # Should handle gracefully, not crash
            assert response.status_code in [200, 404, 400]

    def test_malformed_form_data(self, client):
        """Test handling of malformed form submissions."""
        # Missing required fields
        response1 = client.post("/create/object/", data={})
        assert response1.status_code in [200, 400, 422]

        # Invalid object_id
        response2 = client.post(
            "/create/property/", data={"name": "Test Prop", "object_id": "invalid_id"}
        )
        assert response2.status_code in [200, 400, 422]

    def test_very_long_names(self, client):
        """Test handling of very long names."""
        long_name = "x" * 1000  # Very long name

        response = client.post("/create/object/", data={"name": long_name})
        # Should handle gracefully
        assert response.status_code in [200, 400, 413]


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
        response = client.post("/create/object/", data={"name": "Standard Form"})
        assert response.status_code == 200

        # Should return full page with the new object
        soup = BeautifulSoup(response.content, "html.parser")
        assert soup.find("html") is not None

        objects_list = soup.find("ul", id="objects-list")
        assert objects_list is not None
