"""
Quick Load Test Runner

Ensures all dependencies are available and runs the frontend load test.

Usage:
    python tests/run_load_test.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    required = ["httpx", "beautifulsoup4"]
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("💡 Installing with uv...")
        for package in missing:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package], check=True
            )
        print("✅ Dependencies installed")
    else:
        print("✅ All dependencies available")


async def run_load_test():
    """Import and run the load test."""
    try:
        from tests.load_test_realistic import LoadTestCoordinator

        coordinator = LoadTestCoordinator()
        await coordinator.run_33_user_test(duration_seconds=30)  # Shorter test
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're in the SAVT project directory")


def main():
    """Main entry point."""
    print("🧪 SAVT Load Test Runner")
    print("=" * 40)

    # Check if we're in the right directory
    if not Path("src/main.py").exists():
        print("❌ Not in SAVT project directory")
        print("💡 Run from: /Users/joern/code/SAVT")
        return 1

    # Check dependencies
    check_dependencies()

    # Run the test
    print("\n🚀 Starting load test...")
    asyncio.run(run_load_test())

    return 0


if __name__ == "__main__":
    sys.exit(main())
