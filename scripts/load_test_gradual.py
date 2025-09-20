"""
Gradual Load Test for SAVT Application

Tests with increasing number of concurrent users to find the optimal load level.
Starts with 5 users and increases gradually to identify where issues occur.

Usage:
    # Start the server first
    uvicorn src.main:app --reload

    # Run the gradual load test
    python tests/load_test_gradual.py
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to path so we can import our load test
sys.path.append(str(Path(__file__).parent.parent))

from tests.load_test_realistic import LoadTestCoordinator


async def gradual_test():
    """Run tests with increasing user counts."""
    coordinator = LoadTestCoordinator()

    # Test with different user counts
    user_counts = [5, 10, 15, 20, 25, 30, 33]
    duration = 30  # Shorter tests for quicker feedback

    print("🧪 GRADUAL LOAD TEST")
    print("=" * 50)
    print("Testing with increasing user counts to find optimal load level")
    print()

    results = {}

    for num_users in user_counts:
        print(f"🔍 Testing with {num_users} users...")

        # Check server health before each test
        try:
            await coordinator.check_server_health()
        except SystemExit:
            print(f"❌ Server not responding, stopping at {num_users} users")
            break

        # Reset coordinator state
        coordinator.all_actions = []

        # Run test with current user count
        print(f"🚀 Starting {num_users} concurrent users...")
        tasks = []
        for user_id in range(1, num_users + 1):
            task = coordinator.run_user(user_id, duration)
            tasks.append(task)

        await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate success rate
        total_requests = len(coordinator.all_actions)
        successful_requests = sum(1 for a in coordinator.all_actions if a.success)
        success_rate = (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        )

        results[num_users] = {
            "total": total_requests,
            "success": successful_requests,
            "success_rate": success_rate,
        }

        print(
            f"   📊 {successful_requests}/{total_requests} successful "
            + f"({success_rate:.1f}%)"
        )

        # Stop if success rate is too low
        if success_rate < 50:
            print("⚠️  Success rate dropped below 50%, stopping test")
            break

        print()

    # Summary
    print("=" * 50)
    print("📊 GRADUAL TEST SUMMARY")
    print("=" * 50)

    for users, data in results.items():
        rate = data["success_rate"]
        status = "🟢" if rate >= 95 else "🟡" if rate >= 80 else "🔴"
        print(
            f"{status} {users:2d} users: {data['success']:4d}/{data['total']:4d} "
            + f"({rate:5.1f}%)"
        )

    # Find optimal user count
    good_counts = [u for u, d in results.items() if d["success_rate"] >= 90]
    if good_counts:
        optimal = max(good_counts)
        print(f"\n✅ Optimal user count: {optimal} users (maintains >90% success rate)")
    else:
        print("\n⚠️  No user count achieved >90% success rate")


if __name__ == "__main__":
    asyncio.run(gradual_test())
