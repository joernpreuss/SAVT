"""
Quick Load Test Demo

Demonstrates the load testing system with 3 users for 10 seconds.
Perfect for validating the setup before running the full 33-user test.

Usage:
    # Start the server first:
    TEST_DATABASE=postgresql \
    DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt \
    uvicorn src.main:app --reload

    # Run the demo:
    uv run python tests/test_load_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to path so we can import our load test
sys.path.append(str(Path(__file__).parent.parent))

from tests.load_test_realistic import LoadTestCoordinator


async def main():
    """Run a quick 3-user demo test."""
    print("🎬 LOAD TEST DEMO")
    print("=" * 30)
    print("👥 Users: 3")
    print("⏱️  Duration: 10 seconds")
    print()

    coordinator = LoadTestCoordinator()

    # Override the method to test with fewer users
    async def demo_test():
        """Run demo with 3 users for 10 seconds."""
        print("🧪 Starting demo load test...")

        # Check server health
        await coordinator.check_server_health()

        # Run 3 users concurrently
        tasks = []
        for user_id in range(1, 4):  # Users 1-3
            task = coordinator.run_user(user_id, 10)  # 10 seconds
            tasks.append(task)

        # Wait for completion
        await asyncio.gather(*tasks, return_exceptions=True)

        # Generate report
        await coordinator.generate_report(10.0)

    await demo_test()


if __name__ == "__main__":
    asyncio.run(main())
