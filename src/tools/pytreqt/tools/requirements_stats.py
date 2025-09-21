"""Requirements statistics and detailed reporting."""

import csv
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table


def show_stats(format="text"):
    """Show detailed requirements statistics."""
    # Load valid requirements using same method as coverage report
    from .generate_coverage_report import extract_requirements_from_specs

    valid_requirements_dict = extract_requirements_from_specs()
    valid_requirements = set(valid_requirements_dict.keys())

    # Load test coverage data
    coverage_file = Path("specs/reports/TEST_COVERAGE.md")
    if not coverage_file.exists():
        print(
            "❌ Coverage report not found. "
            + "Run: uv run python -m src.tools.pytreqt coverage"
        )
        return

    # Parse coverage data
    content = coverage_file.read_text()
    tested_requirements = set()
    untested_requirements = set()

    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "**Status**: ✅ **Tested**" in line:
            # Find requirement ID in the line immediately before
            if i > 0:
                prev_line = lines[i - 1]
                if "###" in prev_line and ("FR-" in prev_line or "BR-" in prev_line):
                    req = prev_line.split(":")[0].replace("### ", "").strip()
                    tested_requirements.add(req)
        elif "**Status**: ❌ **Not Tested**" in line:
            if i > 0:
                prev_line = lines[i - 1]
                if "###" in prev_line and ("FR-" in prev_line or "BR-" in prev_line):
                    req = prev_line.split(":")[0].replace("### ", "").strip()
                    untested_requirements.add(req)

    # Calculate statistics
    total_requirements = len(valid_requirements)
    tested_count = len(tested_requirements)
    # Calculate actual untested requirements
    untested_requirements = valid_requirements - tested_requirements
    untested_count = len(untested_requirements)
    coverage_percentage = (
        (tested_count / total_requirements * 100) if total_requirements > 0 else 0
    )

    # Show all requirements
    requirements_to_show = valid_requirements

    # Output in requested format
    if format == "json":
        data = {
            "total_requirements": total_requirements,
            "tested_requirements": tested_count,
            "untested_requirements": untested_count,
            "coverage_percentage": round(coverage_percentage, 1),
            "tested": list(tested_requirements),
            "untested": list(untested_requirements),
        }
        print(json.dumps(data, indent=2))

    elif format == "csv":
        writer = csv.writer(sys.stdout)
        writer.writerow(["Requirement", "Status", "Category"])
        for req in requirements_to_show:
            status = "Tested" if req in tested_requirements else "Not Tested"
            category = "FR" if req.startswith("FR-") else "BR"
            writer.writerow([req, status, category])

    else:  # text format
        console = Console()

        # Overall statistics
        console.print("\n📊 Requirements Coverage Statistics", style="bold blue")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Requirements", str(total_requirements))
        table.add_row("Tested Requirements", str(tested_count))
        table.add_row("Untested Requirements", str(untested_count))
        table.add_row("Coverage Percentage", f"{coverage_percentage:.1f}%")

        console.print(table)

        # Show breakdown by category when all requirements are tested
        if untested_count == 0:
            # Show breakdown by category
            fr_tested = len([r for r in tested_requirements if r.startswith("FR-")])
            br_tested = len([r for r in tested_requirements if r.startswith("BR-")])
            fr_total = len([r for r in valid_requirements if r.startswith("FR-")])
            br_total = len([r for r in valid_requirements if r.startswith("BR-")])

            console.print("\n📋 Breakdown by Category", style="bold blue")

            breakdown_table = Table(show_header=True, header_style="bold magenta")
            breakdown_table.add_column("Category", style="cyan")
            breakdown_table.add_column("Tested", style="green")
            breakdown_table.add_column("Total", style="yellow")
            breakdown_table.add_column("Coverage", style="blue")

            fr_coverage = (fr_tested / fr_total * 100) if fr_total > 0 else 0
            br_coverage = (br_tested / br_total * 100) if br_total > 0 else 0

            breakdown_table.add_row(
                "Functional Requirements (FR)",
                str(fr_tested),
                str(fr_total),
                f"{fr_coverage:.1f}%",
            )
            breakdown_table.add_row(
                "Business Rules (BR)",
                str(br_tested),
                str(br_total),
                f"{br_coverage:.1f}%",
            )

            console.print(breakdown_table)
