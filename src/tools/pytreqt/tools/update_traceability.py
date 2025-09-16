#!/usr/bin/env python3
"""
Update requirements traceability - regenerate coverage and check for changes.
"""

import subprocess
import sys
from pathlib import Path


def _run_command(cmd, description, suppress_output=False):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        if suppress_output:
            subprocess.run(cmd, check=True, cwd=Path.cwd(), capture_output=True)
        else:
            subprocess.run(cmd, check=True, cwd=Path.cwd())
        print(f"✅ {description} completed\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}\n")
        return False


def main():
    """Update all traceability artifacts."""
    if not Path("specs").exists():
        print("ERROR: Run this script from the project root directory")
        sys.exit(1)

    print("🏃 Updating requirements traceability...\n")

    # Check for requirement changes
    print("1️⃣  Checking for requirement changes...")
    try:
        result = subprocess.run(
            ["uv", "run", "python", "pytreqt/tools/change_detector.py"],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
        )
        # Note: change_detector exits with 1 if changes found, 0 if no changes
        if result.returncode == 1:
            print("   ⚠️  Changes detected - continuing with updates...\n")
        else:
            print("   ✅ No changes detected\n")
    except subprocess.CalledProcessError:
        print("   ⚠️  Warning: Could not check for changes\n")

    # Regenerate coverage report
    success = _run_command(
        ["uv", "run", "python", "pytreqt/tools/generate_coverage_report.py"],
        "2️⃣  Regenerating TEST_COVERAGE.md",
        suppress_output=True,
    )

    if not success:
        sys.exit(1)

    # Run tests with requirements coverage
    success = _run_command(
        ["uv", "run", "pytest", "-q"], "3️⃣  Running tests with requirements coverage"
    )

    if success:
        print("🎉 Traceability update completed successfully!")
        print("📋 Check specs/reports/TEST_COVERAGE.md for updated coverage matrix")
    else:
        print("⚠️  Traceability update completed with test failures")
        print("🔍 Review test results and fix any issues")
        sys.exit(1)


if __name__ == "__main__":
    main()
