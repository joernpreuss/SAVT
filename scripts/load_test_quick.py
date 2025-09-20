"""
Configurable Load Test for SAVT Application

A simple wrapper around the main load test coordinator that allows
configuration via environment variables.

Environment Variables:
    USERS: Number of concurrent users (default: 5)
    DURATION: Test duration in seconds (default: 15 for multi-user, 10 for single)

Usage:
    python scripts/load_test_quick.py
    USERS=33 DURATION=30 python scripts/load_test_quick.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add the project root to path so we can import our load test
sys.path.append(str(Path(__file__).parent.parent))

from tests.load_test_realistic import LoadTestCoordinator


async def quick_test():
    """Run a configurable load test."""
    coordinator = LoadTestCoordinator()

    # Get configuration from environment variables
    users = int(os.environ.get("USERS", 5))
    duration = int(os.environ.get("DURATION", 10 if users == 1 else 15))

    print("🧪 LOAD TEST")
    print("=" * 30)
    print(f"Testing {users} users for {duration} seconds")
    print()

    # Check server health
    try:
        await coordinator.check_server_health()
        print("✅ Server health check passed")
    except SystemExit:
        print("❌ Server not responding")
        return

    print()

    # Run the test
    if users == 1:
        print("🚀 Running single user test")
        await coordinator.run_user(1, duration)
    else:
        print(f"🚀 Running {users} concurrent users for {duration}s...")
        start_time = time.time()

        # Run users concurrently
        tasks = []
        for user_id in range(1, users + 1):
            task = coordinator.run_user(user_id, duration)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        print(f"🏁 Test completed in {total_time:.1f} seconds")

    # Quick summary
    total_requests = len(coordinator.all_actions)
    successful_requests = sum(1 for a in coordinator.all_actions if a.success)
    success_rate = (
        (successful_requests / total_requests * 100) if total_requests > 0 else 0
    )

    print("\n" + "=" * 30)
    print("📊 QUICK RESULTS")
    print("=" * 30)
    print(f"Total Requests: {total_requests}")
    print(f"Successful: {successful_requests}")
    print(f"Success Rate: {success_rate:.1f}%")

    if success_rate > 0:
        print("🎉 SUCCESS! The server is handling requests properly!")
    else:
        print("❌ Still having issues")
        # Show a few errors for debugging
        failed = [a for a in coordinator.all_actions if not a.success]
        if failed:
            print("\nSample errors:")
            for _i, failure in enumerate(failed[:3]):
                print(f"  {failure.status_code}: {failure.error_msg}")


if __name__ == "__main__":
    asyncio.run(quick_test())
