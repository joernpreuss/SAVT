"""Debug script to test what's failing in CI."""

import os
import sys
from fastapi.testclient import TestClient

print("=== Debug CI Environment ===")
print(f"Python version: {sys.version}")
print(f"OBJECT_NAME_SINGULAR: {os.getenv('OBJECT_NAME_SINGULAR')}")
print(f"PROPERTY_NAME_SINGULAR: {os.getenv('PROPERTY_NAME_SINGULAR')}")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
print(f"Current working directory: {os.getcwd()}")
print("=== Import Test ===")

try:
    from src.main import app
    print("✅ Successfully imported app")

    client = TestClient(app)
    print("✅ Successfully created TestClient")

    # Test basic route
    response = client.get("/")
    print(f"GET / status: {response.status_code}")

    # Test the failing route
    response = client.post("/api/v1/items", json={"name": "test", "kind": "test"})
    print(f"POST /api/v1/items status: {response.status_code}")
    if response.status_code == 500:
        print(f"Error details: {response.text}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
