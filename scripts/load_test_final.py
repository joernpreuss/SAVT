"""
Final Optimized Load Test for 33 Users

Runs 33 concurrent users with optimized timeouts to complete within 1 minute.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

# Add the project root to path so we can import our load test
sys.path.append(str(Path(__file__).parent.parent))

from tests.load_test_realistic import LoadTestCoordinator


async def final_test():
    """Run optimized 33-user test within 1 minute."""
    coordinator = LoadTestCoordinator()

    print("🧪 FINAL OPTIMIZED LOAD TEST")
    print("=" * 40)
    print("33 users | 20 seconds | 1-minute total timeout")
    print()

    # Check server health
    try:
        await coordinator.check_server_health()
        print("✅ Server health check passed")
    except SystemExit:
        print("❌ Server not responding")
        return

    print()

    # Run the test with shorter duration - run 33 users for 20 seconds
    print(f"🚀 Running 33 users for 20s...")
    start_time = time.time()

    # Run users concurrently
    tasks: list[Any] = []
    for user_id in range(1, 34):  # 33 users
        task = coordinator.run_user(user_id, 20)  # 20 seconds
        tasks.append(task)

    await asyncio.gather(*tasks, return_exceptions=True)

    total_time = time.time() - start_time
    print(f"🏁 Completed in {total_time:.1f} seconds")

    # Generate report
    await coordinator.generate_report(20.0)

    # Quick summary
    total_requests = len(coordinator.all_actions)
    successful_requests = sum(1 for a in coordinator.all_actions if a.success)
    success_rate = (
        (successful_requests / total_requests * 100) if total_requests > 0 else 0
    )

    print("\n" + "=" * 40)
    print("🎯 FINAL RESULTS")
    print("=" * 40)
    print(f"Success Rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print("🟢 EXCELLENT: >90% success rate!")
    elif success_rate >= 75:
        print("🟡 GOOD: >75% success rate")
    elif success_rate >= 50:
        print("🟠 FAIR: >50% success rate")
    else:
        print("🔴 NEEDS WORK: <50% success rate")

    print(f"Total: {successful_requests}/{total_requests} successful requests")


if __name__ == "__main__":
    asyncio.run(final_test())
