#!/usr/bin/env python3
"""
Simple performance test to isolate bottlenecks.

Tests individual operations to understand what's causing slow response times.
"""

import asyncio
import time

import httpx


async def test_individual_operations():
    """Test each operation individually to identify bottlenecks."""
    print("🔍 SIMPLE PERFORMANCE ANALYSIS")
    print("=" * 40)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        operations = [
            ("Homepage", "GET", "/", None),
            (
                "Create unique item",
                "POST",
                "/create/item/",
                {"name": f"PerfTest{int(time.time() * 1000000)}"},
            ),
            (
                "Create unique feature",
                "POST",
                "/create/feature/",
                {"name": f"PerfTestFeat{int(time.time() * 1000000)}"},
            ),
        ]

        for op_name, method, path, data in operations:
            print(f"\n🧪 Testing: {op_name}")

            times = []
            for i in range(3):  # Test each operation 3 times
                start = time.time()
                try:
                    if method == "GET":
                        response = await client.get(f"{base_url}{path}")
                    else:
                        response = await client.post(f"{base_url}{path}", data=data)

                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)

                    print(
                        f"  Attempt {i + 1}: {response.status_code} ({elapsed:.0f}ms)"
                    )

                    # Brief pause between attempts
                    await asyncio.sleep(0.1)

                except Exception as e:
                    elapsed = (time.time() - start) * 1000
                    print(f"  Attempt {i + 1}: ERROR ({elapsed:.0f}ms) - {e}")

            if times:
                avg_time = sum(times) / len(times)
                print(f"  📊 {op_name} average: {avg_time:.0f}ms")


async def test_concurrent_load():
    """Test concurrent requests to see if that's causing the slowdown."""
    print("\n🔍 CONCURRENT LOAD TEST")
    print("=" * 40)

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        print("Testing 5 concurrent homepage requests...")

        tasks = []
        for _i in range(5):
            task = client.get(f"{base_url}/")
            tasks.append(task)

        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start

        successes = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  Request {i}: Exception - {result}")
            elif result.status_code == 200:
                successes += 1
                print(f"  Request {i}: Success (200)")
            else:
                print(f"  Request {i}: Status {result.status_code}")

        print(f"\n📊 Results: {successes}/5 successful in {total_time:.2f}s")
        if successes > 0:
            avg_time = (total_time / successes) * 1000
            print(f"📊 Average response time: {avg_time:.0f}ms")


if __name__ == "__main__":
    asyncio.run(test_individual_operations())
    asyncio.run(test_concurrent_load())
