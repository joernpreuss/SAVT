"""
Frontend Load Testing for 33 Concurrent Users

Tests the SAVT application with 33 concurrent users performing realistic
interactions including HTMX requests, veto/unveto actions, and CRUD operations.

Usage:
    python tests/load_test_frontend.py
"""

import asyncio
import random
import statistics
import time
from dataclasses import dataclass
from typing import Final

import httpx


@dataclass
class LoadTestResult:
    """Results from load testing."""

    user_id: int
    action: str
    status_code: int
    response_time: float
    success: bool
    error: str | None = None


class LoadTestUser:
    """Simulates a single user interacting with the SAVT application."""

    def __init__(self, user_id: int, base_url: str = "http://localhost:8000"):
        self.user_id = user_id
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results: list[LoadTestResult] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _record_result(
        self,
        action: str,
        response: httpx.Response,
        response_time: float,
        error: str | None = None,
    ):
        """Record the result of an action."""
        result = LoadTestResult(
            user_id=self.user_id,
            action=action,
            status_code=response.status_code,
            response_time=response_time,
            success=200 <= response.status_code < 300 and error is None,
            error=error,
        )
        self.results.append(result)
        return result

    async def make_request(self, method: str, url: str, action: str, **kwargs):
        """Make an HTTP request and record timing."""
        start_time = time.time()
        try:
            response = await self.client.request(method, url, **kwargs)
            response_time = time.time() - start_time
            return self._record_result(action, response, response_time)
        except Exception as e:
            response_time = time.time() - start_time

            # Create a dummy response for error cases
            class ErrorResponse:
                status_code = 500

            return self._record_result(action, ErrorResponse(), response_time, str(e))

    async def load_homepage(self):
        """Load the main page to get initial state."""
        return await self.make_request("GET", self.base_url, "load_homepage")

    async def create_item(self, item_name: str):
        """Create a new item."""
        data = {"name": item_name}
        return await self.make_request(
            "POST", f"{self.base_url}/create/item/", "create_item", data=data
        )

    async def create_feature(self, feature_name: str, item_name: str | None = None):
        """Create a new feature, optionally attached to an item."""
        data = {"name": feature_name}
        if item_name:
            data["item"] = item_name
        return await self.make_request(
            "POST", f"{self.base_url}/create/feature/", "create_feature", data=data
        )

    async def veto_feature(
        self, feature_name: str, feature_id: int, item_name: str | None = None
    ):
        """Veto a feature (standalone or item-scoped)."""
        if item_name:
            url = (
                f"{self.base_url}/user/anonymous/veto/item/{item_name}"
                + f"/feature/{feature_name}?feature_id={feature_id}"
            )
        else:
            url = (
                f"{self.base_url}/user/anonymous/veto/feature/{feature_name}"
                + f"?feature_id={feature_id}"
            )

        return await self.make_request("GET", url, "veto_feature")

    async def unveto_feature(
        self, feature_name: str, feature_id: int, item_name: str | None = None
    ):
        """Remove veto from a feature."""
        if item_name:
            url = (
                f"{self.base_url}/user/anonymous/unveto/item/{item_name}"
                + f"/feature/{feature_name}?feature_id={feature_id}"
            )
        else:
            url = (
                f"{self.base_url}/user/anonymous/unveto/feature/{feature_name}"
                + f"?feature_id={feature_id}"
            )

        return await self.make_request("GET", url, "unveto_feature")

    async def move_feature(self, feature_name: str, source_item: str, target_item: str):
        """Move a feature between items."""
        data = {"source_item": source_item, "target_item": target_item}
        return await self.make_request(
            "POST",
            f"{self.base_url}/move/feature/{feature_name}",
            "move_feature",
            data=data,
        )

    async def delete_feature(self, feature_id: int):
        """Delete a feature."""
        return await self.make_request(
            "POST", f"{self.base_url}/delete/feature/{feature_id}", "delete_feature"
        )

    async def simulate_realistic_session(self, duration_seconds: int = 60):
        """Simulate a realistic user session with mixed actions."""
        print(f"🧑‍💻 User {self.user_id} starting session...")

        # Always start by loading the homepage
        await self.load_homepage()
        await asyncio.sleep(random.uniform(0.5, 2.0))  # Think time

        # Create some initial data
        my_item = f"user{self.user_id}_item"
        my_feature = f"user{self.user_id}_feature"

        await self.create_item(my_item)
        await asyncio.sleep(random.uniform(0.2, 1.0))

        await self.create_feature(my_feature, my_item)
        await asyncio.sleep(random.uniform(0.2, 1.0))

        # Main interaction loop
        end_time = time.time() + duration_seconds
        action_count = 0

        while time.time() < end_time:
            # Weighted random actions (more common actions have higher weights)
            actions = [
                ("load_homepage", 20),  # Users refresh/check state
                ("veto_feature", 30),  # Primary user action
                ("unveto_feature", 25),  # Primary user action
                ("create_feature", 15),  # Less common
                ("create_item", 10),  # Less common
            ]

            # Choose action based on weights
            total_weight = sum(weight for _, weight in actions)
            r = random.randint(1, total_weight)
            cumulative = 0

            for action, weight in actions:
                cumulative += weight
                if r <= cumulative:
                    chosen_action = action
                    break

            # Execute the chosen action
            try:
                if chosen_action == "load_homepage":
                    await self.load_homepage()
                elif chosen_action == "veto_feature":
                    # Create a feature ID that might exist
                    feature_id = random.randint(1, 100)
                    await self.veto_feature(my_feature, feature_id, my_item)
                elif chosen_action == "unveto_feature":
                    feature_id = random.randint(1, 100)
                    await self.unveto_feature(my_feature, feature_id, my_item)
                elif chosen_action == "create_feature":
                    new_feature = f"user{self.user_id}_feat_{action_count}"
                    await self.create_feature(new_feature, my_item)
                elif chosen_action == "create_item":
                    new_item = f"user{self.user_id}_item_{action_count}"
                    await self.create_item(new_item)

                action_count += 1

                # Realistic user think time
                await asyncio.sleep(random.uniform(0.1, 3.0))

            except Exception as e:
                print(f"❌ User {self.user_id} error in {chosen_action}: {e}")
                continue

        print(f"✅ User {self.user_id} completed session with {action_count} actions")


class LoadTestRunner:
    """Coordinates load testing with multiple concurrent users."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.all_results: list[LoadTestResult] = []

    async def run_load_test(self, num_users: int = 33, duration_seconds: int = 60):
        """Run load test with specified number of concurrent users."""
        print(
            f"🚀 Starting load test with {num_users} concurrent users "
            + f"for {duration_seconds}s..."
        )
        print(f"🎯 Target: {self.base_url}")
        print()

        start_time = time.time()

        # Create and run all users concurrently
        tasks = []
        for user_id in range(1, num_users + 1):
            task = self._run_single_user(user_id, duration_seconds)
            tasks.append(task)

        # Wait for all users to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time
        print(f"\n🏁 Load test completed in {total_time:.2f} seconds")

        # Generate report
        self.generate_report(num_users, duration_seconds, total_time)

    async def _run_single_user(self, user_id: int, duration_seconds: int):
        """Run a single user's session."""
        try:
            async with LoadTestUser(user_id, self.base_url) as user:
                await user.simulate_realistic_session(duration_seconds)
                self.all_results.extend(user.results)
        except Exception as e:
            print(f"💥 User {user_id} failed: {e}")

    def generate_report(self, num_users: int, duration_seconds: int, total_time: float):
        """Generate and display load test results."""
        print("\n" + "=" * 60)
        print("📊 LOAD TEST RESULTS")
        print("=" * 60)

        if not self.all_results:
            print("❌ No results collected!")
            return

        # Basic statistics
        total_requests = len(self.all_results)
        successful_requests = sum(1 for r in self.all_results if r.success)
        failed_requests = total_requests - successful_requests
        success_rate = (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0
        )

        print(f"👥 Users: {num_users}")
        print(f"⏱️  Duration: {duration_seconds}s (actual: {total_time:.2f}s)")
        print(f"📈 Total Requests: {total_requests}")
        print(f"✅ Successful: {successful_requests} ({success_rate:.1f}%)")
        print(f"❌ Failed: {failed_requests}")
        print()

        # Response time statistics
        response_times = [
            r.response_time * 1000 for r in self.all_results if r.success
        ]  # Convert to ms
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = sorted(response_times)[int(0.95 * len(response_times))]
            p99_response_time = sorted(response_times)[int(0.99 * len(response_times))]

            print("⚡ Response Times (ms):")
            print(f"   Average: {avg_response_time:.1f}ms")
            print(f"   Median:  {median_response_time:.1f}ms")
            print(f"   95th %:  {p95_response_time:.1f}ms")
            print(f"   99th %:  {p99_response_time:.1f}ms")
            print()

        # Throughput
        requests_per_second = total_requests / total_time
        successful_rps = successful_requests / total_time

        print("🚀 Throughput:")
        print(f"   Total RPS: {requests_per_second:.1f}")
        print(f"   Success RPS: {successful_rps:.1f}")
        print()

        # Action breakdown
        action_counts = {}
        action_success = {}
        for result in self.all_results:
            action = result.action
            action_counts[action] = action_counts.get(action, 0) + 1
            if result.success:
                action_success[action] = action_success.get(action, 0) + 1

        print("📋 Action Breakdown:")
        for action in sorted(action_counts.keys()):
            total = action_counts[action]
            success = action_success.get(action, 0)
            success_pct = (success / total * 100) if total > 0 else 0
            print(f"   {action:15}: {total:4} requests ({success_pct:5.1f}% success)")

        # Error analysis
        errors = [r for r in self.all_results if not r.success]
        if errors:
            print(f"\n⚠️  Errors ({len(errors)} total):")
            error_counts: dict[str, int] = {}
            for error in errors:
                key = f"{error.status_code}: {error.error or 'HTTP Error'}"
                error_counts[key] = error_counts.get(key, 0) + 1

            for error_type, count in sorted(
                error_counts.items(), key=lambda x: (x[1]), reverse=True
            )[:5]:
                print(f"   {error_type}: {count}")

        print("\n" + "=" * 60)

        # Performance assessment
        print("🎯 PERFORMANCE ASSESSMENT:")
        if success_rate >= 99:
            print("🟢 Excellent: >99% success rate")
        elif success_rate >= 95:
            print("🟡 Good: >95% success rate")
        else:
            print("🔴 Needs Attention: <95% success rate")

        if response_times and avg_response_time < 500:
            print("🟢 Excellent: Average response time <500ms")
        elif response_times and avg_response_time < 1000:
            print("🟡 Good: Average response time <1000ms")
        elif response_times:
            print("🔴 Slow: Average response time >1000ms")

        if successful_rps >= 50:
            print("🟢 High Throughput: >50 successful requests/sec")
        elif successful_rps >= 20:
            print("🟡 Moderate Throughput: >20 successful requests/sec")
        else:
            print("🔴 Low Throughput: <20 successful requests/sec")


async def main():
    """Main entry point for load testing."""
    # Test configuration
    NUM_USERS: Final = 33
    DURATION_SECONDS: Final = 60
    BASE_URL: Final = "http://localhost:8000"

    print("🧪 SAVT Frontend Load Test")
    print(f"🎯 Simulating {NUM_USERS} concurrent users")
    print(f"⏱️  Test duration: {DURATION_SECONDS} seconds")
    print(f"🌐 Target URL: {BASE_URL}")
    print()

    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_URL, timeout=5.0)
            if response.status_code == 200:
                print("✅ Server is running and accessible")
            else:
                print(f"⚠️  Server responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Make sure the SAVT server is running: uvicorn src.main:app --reload")
        return

    print()

    # Run the load test
    runner = LoadTestRunner(BASE_URL)
    await runner.run_load_test(NUM_USERS, DURATION_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
