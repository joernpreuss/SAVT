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
        from .change_detector import RequirementChangeDetector

        detector = RequirementChangeDetector()
        changes = detector.detect_changes()
        if changes["file_changed"]:
            print("   ⚠️  Changes detected - continuing with updates...\n")
        else:
            print("   ✅ No changes detected\n")
    except Exception:
        print("   ⚠️  Warning: Could not check for changes\n")

    # Regenerate coverage report
    print("🔄 2️⃣  Regenerating TEST_COVERAGE.md...")
    try:
        from .generate_coverage_report import main as generate_main

        generate_main()
        print("✅ 2️⃣  Regenerating TEST_COVERAGE.md completed\n")
        success = True
    except Exception as e:
        print(f"❌ 2️⃣  Regenerating TEST_COVERAGE.md failed: {e}\n")
        success = False

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
