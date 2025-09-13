#!/usr/bin/env python3
"""
Generate TEST_COVERAGE.md from requirements and test coverage data.
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def extract_requirements_from_specs():
    """Extract all defined requirements from REQUIREMENTS.md."""
    requirements_file = Path("specs/spec/REQUIREMENTS.md")
    if not requirements_file.exists():
        print("ERROR: specs/spec/REQUIREMENTS.md not found")
        return {}

    content = requirements_file.read_text(encoding="utf-8")
    requirements = {}

    # Extract FR and BR requirements with descriptions
    # Pattern matches lines like "- **FR-1.1**: Users can create objects"
    pattern = r"-\s+\*\*((?:FR|BR)-\d+\.?\d*)\*\*:\s+(.+)"
    matches = re.findall(pattern, content, re.MULTILINE)

    for req_id, description in matches:
        requirements[req_id.upper()] = description.strip()

    return requirements


def get_test_coverage():
    """Run pytest to get requirements coverage data."""
    try:
        # Run pytest with requirements analysis only
        result = subprocess.run(
            ["uv", "run", "pytest", "--requirements-only", "-v"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )

        if result.returncode != 0 and "skipped" not in result.stdout:
            print(f"ERROR running pytest: {result.stderr}")
            return {}

        # Parse the requirements coverage output
        coverage_data = defaultdict(list)
        lines = result.stdout.split('\n')

        current_req = None
        for line in lines:
            line = line.strip()

            # Look for requirement headers like "  BR-3.3:"
            if re.match(r'^[A-Z]+-\d+\.?\d*:$', line):
                current_req = line.rstrip(':')

            # Look for test entries like "    ⊝ test_veto_idempotency"
            elif current_req and line.startswith('⊝'):
                test_name = line[2:].strip()  # Remove "⊝ " prefix
                coverage_data[current_req].append(test_name)

        return coverage_data

    except Exception as e:
        print(f"ERROR getting test coverage: {e}")
        return {}


def generate_coverage_matrix():
    """Generate the complete coverage matrix."""
    print("Extracting requirements from specifications...")
    all_requirements = extract_requirements_from_specs()

    print("Analyzing test coverage...")
    test_coverage = get_test_coverage()

    if not all_requirements:
        print("No requirements found!")
        return

    # Generate the coverage report
    report_lines = [
        "# Test Coverage Matrix",
        "",
        "This document shows the traceability between functional requirements (FR), business rules (BR), and test cases.",
        "",
        f"**Generated**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**",
        "",
        "## Coverage Summary",
        "",
        f"- **Total Requirements**: {len(all_requirements)}",
        f"- **Requirements with Tests**: {len(test_coverage)}",
        f"- **Requirements without Tests**: {len(all_requirements) - len(test_coverage)}",
        "",
        f"**Coverage Percentage**: {len(test_coverage) / len(all_requirements) * 100:.1f}%",
        "",
        "## Requirements Coverage",
        ""
    ]

    # Sort requirements by ID
    sorted_requirements = sorted(all_requirements.items())

    for req_id, description in sorted_requirements:
        tests = test_coverage.get(req_id, [])
        status = "✅ **Tested**" if tests else "❌ **Not Tested**"

        report_lines.extend([
            f"### {req_id}: {description}",
            f"**Status**: {status}",
            ""
        ])

        if tests:
            report_lines.append("**Test Cases**:")
            for test in tests:
                report_lines.append(f"- `{test}`")
            report_lines.append("")
        else:
            report_lines.extend([
                "**Test Cases**: None",
                "⚠️ *This requirement needs test coverage*",
                ""
            ])

    # Add untested requirements section
    untested = [req for req in all_requirements if req not in test_coverage]
    if untested:
        report_lines.extend([
            "## Requirements Needing Tests",
            "",
            "The following requirements have no test coverage:",
            ""
        ])

        for req_id in sorted(untested):
            description = all_requirements[req_id]
            report_lines.append(f"- **{req_id}**: {description}")

        report_lines.append("")

    # Add test statistics
    total_tests = sum(len(tests) for tests in test_coverage.values())
    report_lines.extend([
        "## Test Statistics",
        "",
        f"- **Total Test Cases with Requirements**: {total_tests}",
        f"- **Unique Requirements Tested**: {len(test_coverage)}",
        f"- **Average Tests per Requirement**: {total_tests / len(test_coverage):.1f}" if test_coverage else "- **Average Tests per Requirement**: 0",
        "",
        "---",
        "",
        "*This file is auto-generated by `pytreqt/generate_coverage_report.py`*",
        "*To update, run: `uv run python pytreqt/generate_coverage_report.py`*"
    ])

    return '\n'.join(report_lines)


def main():
    """Main function to generate and write the coverage report."""
    # Ensure we're in the right directory
    if not Path("specs").exists():
        print("ERROR: Run this script from the project root directory")
        sys.exit(1)

    # Generate the report
    report_content = generate_coverage_matrix()
    if not report_content:
        print("Failed to generate coverage report")
        sys.exit(1)

    # Write to the reports directory
    reports_dir = Path("specs/reports")
    reports_dir.mkdir(exist_ok=True)

    coverage_file = reports_dir / "TEST_COVERAGE.md"
    coverage_file.write_text(report_content, encoding="utf-8")

    print(f"✅ Coverage report generated: {coverage_file}")
    print(f"📊 Coverage summary: {len(extract_requirements_from_specs())} total requirements")


if __name__ == "__main__":
    main()
