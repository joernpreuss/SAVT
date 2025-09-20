"""
Realistic Load Test for SAVT Application

Simulates 33 concurrent users performing actual HTMX-based interactions
as they would in the real application.

This test focuses on:
1. Loading the homepage and parsing current state
2. Veto/unveto actions (primary use case)
3. Creating items and features
4. Realistic user behavior patterns

Usage:
    # Start the server first
    uvicorn src.main:app --reload

    # Run the load test
    python tests/load_test_realistic.py
"""

import asyncio
import random
import re
import statistics
import time
from dataclasses import dataclass
from urllib.parse import quote

import httpx


@dataclass
class UserAction:
    """Represents a user action and its result."""

    timestamp: float
    user_id: int
    action_type: str
    target: str
    status_code: int
    response_time_ms: float
    success: bool
    error_msg: str | None = None


class RealisticUser:
    """Simulates a realistic user with HTMX interactions."""

    def __init__(self, user_id: int, base_url: str = "http://localhost:8000"):
        self.user_id = user_id
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),  # Increased timeout for high load
            limits=httpx.Limits(
                max_connections=20,  # Allow more connections per client
                max_keepalive_connections=10,
            ),
            headers={
                "User-Agent": f"LoadTest-User-{user_id}",
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.5",
                "HX-Request": "true",  # Simulate HTMX requests
                "Connection": "keep-alive",  # Reuse connections
            },
        )
        self.actions: list[UserAction] = []
        self.current_items: list[str] = []
        self.current_features: list[
            tuple[str, int, str | None]
        ] = []  # (name, id, item)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _record_action(
        self,
        action_type: str,
        target: str,
        start_time: float,
        response: httpx.Response,
        error_msg: str | None = None,
    ):
        """Record an action for analysis."""
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        success = 200 <= response.status_code < 400 and error_msg is None

        action = UserAction(
            timestamp=time.time(),
            user_id=self.user_id,
            action_type=action_type,
            target=target,
            status_code=response.status_code,
            response_time_ms=response_time,
            success=success,
            error_msg=error_msg,
        )
        self.actions.append(action)
        return action

    async def make_request(
        self, method: str, url: str, action_type: str, target: str, **kwargs
    ) -> UserAction:
        """Make an HTTP request and record metrics."""
        start_time = time.time()
        try:
            response = await self.client.request(method, url, **kwargs)
            return self._record_action(action_type, target, start_time, response)
        except httpx.TimeoutException as e:
            # Timeout - server overloaded
            class TimeoutResponse:
                status_code = 408  # Request Timeout

            return self._record_action(
                action_type, target, start_time, TimeoutResponse(), f"Timeout: {e}"
            )
        except httpx.ConnectError as e:
            # Connection failed - server unreachable
            class ConnectResponse:
                status_code = 503  # Service Unavailable

            return self._record_action(
                action_type, target, start_time, ConnectResponse(), f"Connection: {e}"
            )
        except Exception as e:
            # Other errors
            class ErrorResponse:
                status_code = 500

            return self._record_action(
                action_type, target, start_time, ErrorResponse(), f"Error: {e}"
            )

    def _parse_features_from_html(self, html: str):
        """Extract features and their IDs from HTML response."""
        features = []

        # Look for feature IDs in the HTML
        # Pattern matches: feature-123 or data-feature-id="123"
        id_patterns = [
            r'id="feature-(\d+)"',
            r'data-feature-id="(\d+)"',
            r"feature_id=(\d+)",
        ]

        for pattern in id_patterns:
            matches = re.findall(pattern, html)
            features.extend([int(match) for match in matches])

        # Also look for feature names in veto/unveto links
        name_pattern = r'/feature/([^/?]+)(?:\?|")'
        names = re.findall(name_pattern, html)

        # Combine IDs and names (simplified - in real app we'd parse more carefully)
        if features and names:
            self.current_features = [
                (name, feature_id, None)
                for name, feature_id in zip(
                    names[: len(features)], features, strict=False
                )
            ]

    async def load_homepage(self) -> UserAction:
        """Load homepage and parse current state."""
        action = await self.make_request("GET", self.base_url, "homepage", "main")

        if action.success:
            # Parse the response to get current items/features
            try:
                response = await self.client.get(self.base_url)
                html = response.text
                self._parse_features_from_html(html)
            except Exception:  # noqa: S110
                pass  # Continue even if parsing fails

        return action

    async def create_item(self, item_name: str) -> UserAction:
        """Create a new item."""
        data = {"name": item_name}
        action = await self.make_request(
            "POST", f"{self.base_url}/create/item/", "create_item", item_name, data=data
        )

        if action.success:
            self.current_items.append(item_name)

        return action

    async def create_feature(
        self, feature_name: str, item_name: str | None = None
    ) -> UserAction:
        """Create a new feature."""
        data = {"name": feature_name}
        if item_name:
            data["item"] = item_name

        action = await self.make_request(
            "POST",
            f"{self.base_url}/create/feature/",
            "create_feature",
            feature_name,
            data=data,
        )

        # Add to our tracking (with dummy ID)
        if action.success:
            new_id = random.randint(1000, 9999)  # Dummy ID
            self.current_features.append((feature_name, new_id, item_name))

        return action

    async def veto_feature(
        self, feature_name: str, feature_id: int, item_name: str | None = None
    ) -> UserAction:
        """Veto a feature - the primary user action."""
        if item_name:
            url = (
                f"{self.base_url}/user/anonymous/veto/item/{quote(item_name)}"
                + f"/feature/{quote(feature_name)}?feature_id={feature_id}"
            )
        else:
            url = (
                f"{self.base_url}/user/anonymous/veto/feature/{quote(feature_name)}"
                + f"?feature_id={feature_id}"
            )

        return await self.make_request(
            "GET", url, "veto", f"{feature_name}({feature_id})"
        )

    async def unveto_feature(
        self, feature_name: str, feature_id: int, item_name: str | None = None
    ) -> UserAction:
        """Remove veto from a feature."""
        if item_name:
            url = (
                f"{self.base_url}/user/anonymous/unveto/item/{quote(item_name)}"
                + f"/feature/{quote(feature_name)}?feature_id={feature_id}"
            )
        else:
            url = (
                f"{self.base_url}/user/anonymous/unveto/feature/{quote(feature_name)}"
                + f"?feature_id={feature_id}"
            )

        return await self.make_request(
            "GET", url, "unveto", f"{feature_name}({feature_id})"
        )

    async def realistic_session(self, duration_seconds: int = 60):
        """Simulate a realistic user session."""
        print(f"🧑‍💻 User {self.user_id} starting {duration_seconds}s session...")

        # Always start with loading the homepage
        await self.load_homepage()
        await asyncio.sleep(random.uniform(1.0, 3.0))  # Initial page load time

        # Create some initial content for this user with unique timestamps
        session_id = int(time.time() * 1000) % 100000  # Last 5 digits of timestamp
        user_item = f"User{self.user_id}Item{session_id}"
        await self.create_item(user_item)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        user_feature = f"User{self.user_id}Feature{session_id}"
        await self.create_feature(user_feature, user_item)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Main interaction loop - realistic user behavior
        session_end = time.time() + duration_seconds
        actions_performed = 0

        while time.time() < session_end:
            # Realistic action weights based on typical user behavior
            action_choices = [
                ("homepage", 15),  # Check current state
                ("veto", 35),  # Primary action - veto features
                ("unveto", 30),  # Primary action - remove vetos
                ("create_feature", 12),  # Add new features occasionally
                ("create_item", 8),  # Add new items less often
            ]

            # Weighted random choice
            total_weight = sum(w for _, w in action_choices)
            rand = random.randint(1, total_weight)
            cumulative = 0
            chosen_action = "homepage"

            for action, weight in action_choices:
                cumulative += weight
                if rand <= cumulative:
                    chosen_action = action
                    break

            try:
                if chosen_action == "homepage":
                    await self.load_homepage()

                elif chosen_action == "veto":
                    if self.current_features:
                        # Choose a random feature to veto
                        feature_name, feature_id, item_name = random.choice(
                            self.current_features
                        )
                        await self.veto_feature(feature_name, feature_id, item_name)
                    else:
                        # Fallback: try to veto user's own feature
                        await self.veto_feature(
                            user_feature, random.randint(1, 100), user_item
                        )

                elif chosen_action == "unveto":
                    if self.current_features:
                        feature_name, feature_id, item_name = random.choice(
                            self.current_features
                        )
                        await self.unveto_feature(feature_name, feature_id, item_name)
                    else:
                        await self.unveto_feature(
                            user_feature, random.randint(1, 100), user_item
                        )

                elif chosen_action == "create_feature":
                    # Use microsecond timestamp to ensure uniqueness
                    unique_id = int(time.time() * 1000000) % 1000000
                    new_feature = f"User{self.user_id}Feat{unique_id}"
                    target_item = (
                        user_item if random.random() < 0.7 else None
                    )  # 70% attach to item
                    await self.create_feature(new_feature, target_item)

                elif chosen_action == "create_item":
                    unique_id = int(time.time() * 1000000) % 1000000
                    new_item = f"User{self.user_id}Item{unique_id}"
                    await self.create_item(new_item)

                actions_performed += 1

                # Realistic user think time - varies by action type
                if chosen_action == "homepage":
                    think_time = random.uniform(0.5, 2.0)  # Quick page checks
                elif chosen_action in ["veto", "unveto"]:
                    think_time = random.uniform(0.2, 1.0)  # Quick decisions
                else:
                    think_time = random.uniform(1.0, 4.0)  # More thought for creation

                await asyncio.sleep(think_time)

            except Exception as e:
                print(f"❌ User {self.user_id} error during {chosen_action}: {e}")
                await asyncio.sleep(1.0)  # Brief pause on error

        print(f"✅ User {self.user_id} completed {actions_performed} actions")


class LoadTestCoordinator:
    """Coordinates the load test and analyzes results."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.all_actions: list[UserAction] = []

    async def run_33_user_test(self, duration_seconds: int = 60):
        """Run the main 33-user concurrent test."""
        print("🚀 SAVT FRONTEND LOAD TEST")
        print("=" * 50)
        print("👥 Users: 33 concurrent")
        print(f"⏱️  Duration: {duration_seconds} seconds")
        print(f"🌐 URL: {self.base_url}")
        print()

        # Verify server is accessible
        await self.check_server_health()

        print("🏃‍♀️ Starting 33 concurrent users...")
        start_time = time.time()

        # Launch all 33 users concurrently
        tasks = []
        for user_id in range(1, 34):  # Users 1-33
            task = self.run_user(user_id, duration_seconds)
            tasks.append(task)

        # Wait for all users to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        for i, result in enumerate(results, 1):
            if isinstance(result, Exception):
                print(f"💥 User {i} crashed: {result}")

        total_time = time.time() - start_time
        print(f"\n🏁 Test completed in {total_time:.1f} seconds")

        # Generate comprehensive report
        await self.generate_report(total_time)

    async def check_server_health(self):
        """Verify the server is running and responsive."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, timeout=5.0)
                if response.status_code == 200:
                    print("✅ Server health check passed")
                else:
                    print(f"⚠️  Server returned status {response.status_code}")
        except Exception as e:
            print(f"❌ Server health check failed: {e}")
            print("💡 Make sure to start: uvicorn src.main:app --reload")
            raise SystemExit(1) from None

    async def run_user(self, user_id: int, duration: int):
        """Run a single user session."""
        try:
            async with RealisticUser(user_id, self.base_url) as user:
                await user.realistic_session(duration)
                self.all_actions.extend(user.actions)
        except Exception as e:
            print(f"💥 User {user_id} failed: {e}")

    async def generate_report(self, total_time: float):
        """Generate detailed performance report."""
        if not self.all_actions:
            print("❌ No data collected!")
            return

        print("\n" + "=" * 60)
        print("📊 DETAILED RESULTS")
        print("=" * 60)

        # Basic metrics
        total_requests = len(self.all_actions)
        successful = [a for a in self.all_actions if a.success]
        failed = [a for a in self.all_actions if not a.success]

        success_rate = len(successful) / total_requests * 100
        throughput = total_requests / total_time
        successful_throughput = len(successful) / total_time

        print(f"📈 Total Requests: {total_requests}")
        print(f"✅ Successful: {len(successful)} ({success_rate:.1f}%)")
        print(f"❌ Failed: {len(failed)} ({100 - success_rate:.1f}%)")
        print(f"🚀 Throughput: {throughput:.1f} requests/sec")
        print(f"💚 Success Throughput: {successful_throughput:.1f} req/sec")
        print()

        # Response time analysis
        if successful:
            response_times = [a.response_time_ms for a in successful]
            avg_rt = statistics.mean(response_times)
            median_rt = statistics.median(response_times)
            p95_rt = sorted(response_times)[int(0.95 * len(response_times))]
            p99_rt = sorted(response_times)[int(0.99 * len(response_times))]

            print("⚡ Response Times:")
            print(f"   Average: {avg_rt:.0f}ms")
            print(f"   Median:  {median_rt:.0f}ms")
            print(f"   95th %:  {p95_rt:.0f}ms")
            print(f"   99th %:  {p99_rt:.0f}ms")
            print()

        # Action breakdown
        action_stats = {}
        for action in self.all_actions:
            action_type = action.action_type
            if action_type not in action_stats:
                action_stats[action_type] = {"total": 0, "success": 0, "avg_time": 0}

            action_stats[action_type]["total"] += 1
            if action.success:
                action_stats[action_type]["success"] += 1

        # Calculate average times for successful requests
        for action_type in action_stats:
            times = [
                a.response_time_ms
                for a in self.all_actions
                if a.action_type == action_type and a.success
            ]
            if times:
                action_stats[action_type]["avg_time"] = statistics.mean(times)

        print("📋 Action Performance:")
        for action_type, stats in sorted(action_stats.items()):
            total = stats["total"]
            success = stats["success"]
            success_pct = success / total * 100 if total > 0 else 0
            avg_time = stats["avg_time"]

            print(
                f"   {action_type:15}: {total:4} req, {success_pct:5.1f}% success, "
                + f"{avg_time:6.0f}ms avg"
            )

        # Error analysis
        if failed:
            print(f"\n⚠️  Error Analysis ({len(failed)} failures):")
            error_counts: dict[str, int] = {}
            for failure in failed:
                error_key = (
                    f"{failure.status_code}: {failure.error_msg or 'HTTP Error'}"
                )
                error_counts[error_key] = error_counts.get(error_key, 0) + 1

            for error, count in sorted(
                error_counts.items(), key=lambda x: (x[1]), reverse=True
            )[:5]:
                print(f"   {error}: {count} occurrences")

        # Final assessment
        print("\n" + "=" * 60)
        print("🎯 PERFORMANCE VERDICT:")

        if success_rate >= 99:
            print("🟢 EXCELLENT: >99% success rate")
        elif success_rate >= 95:
            print("🟡 GOOD: >95% success rate")
        else:
            print("🔴 POOR: <95% success rate - needs investigation")

        if successful and avg_rt < 200:
            print("🟢 EXCELLENT: Average response <200ms")
        elif successful and avg_rt < 500:
            print("🟡 GOOD: Average response <500ms")
        elif successful:
            print("🔴 SLOW: Average response >500ms")

        if successful_throughput > 100:
            print("🟢 HIGH THROUGHPUT: >100 successful requests/sec")
        elif successful_throughput > 50:
            print("🟡 MODERATE THROUGHPUT: >50 successful requests/sec")
        else:
            print("🔴 LOW THROUGHPUT: <50 successful requests/sec")

        print("\n✨ 33-user concurrent test completed!")


async def main():
    """Run the load test."""
    coordinator = LoadTestCoordinator()
    await coordinator.run_33_user_test(
        duration_seconds=30
    )  # Reduced to 30s for 1min total


if __name__ == "__main__":
    asyncio.run(main())
