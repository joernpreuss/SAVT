"""
Analyze failure patterns to identify optimization opportunities.
"""

import asyncio
import random
import time
from typing import Any
from collections.abc import Sequence

import httpx


async def test_create_item_failures():
    """Test what causes create item failures."""
    print("🔍 ANALYZING CREATE ITEM FAILURES")
    print("=" * 40)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test concurrent item creation with same names
        print("Testing duplicate name conflicts...")

        tasks: list[Any] = []
        for _i in range(5):
            # All try to create the same item name
            task = client.post(
                f"{base_url}/create/item/", data={"name": "ConflictTest"}
            )
            tasks.append(task)

        results: Sequence[Any | Exception] = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  Task {i}: Exception - {result}")
            else:
                print(f"  Task {i}: Status {result.status_code}")

        print("\nTesting rapid sequential creation...")

        # Test rapid sequential creation
        for i in range(10):
            start = time.time()
            try:
                response = await client.post(
                    f"{base_url}/create/item/", data={"name": f"Sequential{i}"}
                )
                elapsed = (time.time() - start) * 1000
                print(f"  Item {i}: {response.status_code} ({elapsed:.0f}ms)")
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                print(f"  Item {i}: ERROR ({elapsed:.0f}ms) - {e}")

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.1)


async def test_response_time_patterns():
    """Analyze what causes slow response times."""
    print("\n🔍 ANALYZING RESPONSE TIME PATTERNS")
    print("=" * 40)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test different operations
        operations: list[tuple[str, str, str, dict[str, str] | None]] = [
            ("homepage", "GET", "/", None),
            (
                "create_item",
                "POST",
                "/create/item/",
                {"name": f"TestItem{random.randint(1000, 9999)}"},
            ),
            (
                "create_feature",
                "POST",
                "/create/feature/",
                {"name": f"TestFeat{random.randint(1000, 9999)}"},
            ),
        ]

        for op_name, method, path, data in operations:
            op_name: str
            method: str
            path: str
            data: dict[str, str] | None
            times: list[float] = []

            for i in range(5):
                start = time.time()
                try:
                    if method == "GET":
                        response = await client.get(f"{base_url}{path}")
                    else:
                        response = await client.post(f"{base_url}{path}", data=data)

                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)
                    print(
                        f"  {op_name} {i + 1}: {response.status_code} ({elapsed:.0f}ms)"
                    )

                except Exception as e:
                    elapsed = (time.time() - start) * 1000
                    print(f"  {op_name} {i + 1}: ERROR ({elapsed:.0f}ms) - {e}")

                await asyncio.sleep(0.2)

            if times:
                avg_time = sum(times) / len(times)
                print(f"  {op_name} average: {avg_time:.0f}ms")
            print()


async def test_connection_limits():
    """Test if we're hitting connection limits."""
    print("🔍 ANALYZING CONNECTION LIMITS")
    print("=" * 40)

    base_url = "http://localhost:8000"

    # Test with many concurrent connections
    async with httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    ) as client:
        print("Testing 20 concurrent homepage requests...")

        tasks: list[Any] = []
        for _i in range(20):
            task = client.get(f"{base_url}/")
            tasks.append(task)

        start = time.time()
        results: Sequence[Any | Exception] = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start

        successes = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  Request {i}: Exception - {result}")
            elif result.status_code == 200:
                successes += 1
            else:
                print(f"  Request {i}: Status {result.status_code}")

        print(f"\nResults: {successes}/20 successful in {total_time:.2f}s")
        print(f"Success rate: {successes / 20 * 100:.1f}%")


async def main():
    """Run all failure analysis tests."""
    await test_create_item_failures()
    await test_response_time_patterns()
    await test_connection_limits()


if __name__ == "__main__":
    asyncio.run(main())
