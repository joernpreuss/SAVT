"""
Debug URL generation to find where special characters come from
"""

import asyncio
import sys
from pathlib import Path
from urllib.parse import quote

# Add the project root to path
sys.path.append(str(Path(__file__).parent.parent))

from tests.load_test_realistic import RealisticUser


async def debug_urls():
    """Debug URL generation."""
    print("🔍 DEBUGGING URL GENERATION")
    print("=" * 40)

    user = RealisticUser(1)

    # Test various feature names
    test_names = [
        "simple",
        "User1Feat0",
        "test feature",  # Space
        "test\nfeature",  # Newline
        "test\rfeature",  # Carriage return
        "test%20feature",  # URL encoded space
        "café",  # Unicode
    ]

    for name in test_names:
        print(f"\nTesting name: {repr(name)}")

        # Without URL encoding
        url1 = (
            f"http://localhost:8000/user/anonymous/veto/feature/{name}?feature_id=123"
        )
        print(f"  Raw URL: {repr(url1)}")

        # With URL encoding
        url2 = f"http://localhost:8000/user/anonymous/veto/feature/{quote(name)}?feature_id=123"
        print(f"  Encoded: {repr(url2)}")

        # Try making a request
        try:
            action = await user.make_request("GET", url2, "test", name)
            print(f"  Result: {action.status_code} - {action.error_msg}")
        except Exception as e:
            print(f"  Error: {e}")

    await user.client.aclose()


if __name__ == "__main__":
    asyncio.run(debug_urls())
