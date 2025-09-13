#!/usr/bin/env python3
"""SAVT Code Quality Checker"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

console = Console()


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        console.print(f"❌ {description} failed", style="red")
        return False


def check_trailing_newlines(fix: bool = False) -> bool:
    """Check and optionally fix trailing newlines."""
    extensions = [
        "*.py",
        "*.md",
        "*.toml",
        "*.yml",
        "*.yaml",
        "*.sh",
        ".gitignore",
        "*.txt",
        "*.json",
        "*.html",
        "*.css",
    ]

    exclude_dirs = {".venv", ".git", ".pytest_cache", ".ruff_cache", ".mypy_cache"}

    missing_files = []

    # Check files with extensions
    for pattern in extensions:
        for file_path in Path(".").rglob(pattern):
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.is_file() and file_path.stat().st_size > 0:
                with open(file_path, "rb") as f:
                    f.seek(-1, 2)  # Go to last byte
                    if f.read(1) != b"\n":
                        missing_files.append(file_path)

    # Check specific root-level executable scripts
    root_executables = ["pytreqt", "qa"]
    for name in root_executables:
        file_path = Path(name)
        if file_path.is_file() and file_path.stat().st_size > 0:
            with open(file_path, "rb") as f:
                f.seek(-1, 2)  # Go to last byte
                if f.read(1) != b"\n":
                    missing_files.append(file_path)

    if missing_files:
        console.print("❌ Files missing trailing newlines:", style="red")
        for file_path in missing_files:
            console.print(f"  {file_path}", style="dim")

        if fix:
            for file_path in missing_files:
                with open(file_path, "a") as f:
                    f.write("\n")
            console.print("✅ Added trailing newlines", style="green")
            return True
        else:
            console.print(
                "Run with --fix-newlines to auto-fix these issues", style="yellow"
            )
            return False
    else:
        console.print("✅ All files have proper trailing newlines", style="green")
        return True


@click.group(invoke_without_command=True)
@click.pass_context
@click.help_option("-h", "--help")
def cli(ctx):
    """SAVT Quality Assurance Tool

    \b
    Examples:
      qa check                   - run all checks (no fixes)
      qa check --fix-all         - run checks with all fixes
      qa check --fix-format      - fix formatting only
      qa check --fix-lint        - fix linting only
      qa check --fix-newlines    - fix newlines only
      qa check --skip-tests      - skip test execution
      qa check fix-all           - equivalent to 'qa check --fix-all'
      qa fix-all                 - shortcut for 'qa check --fix-all'
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group(invoke_without_command=True)
@click.help_option("-h", "--help")
@click.option("--fix-all", is_flag=True, help="Auto-fix all issues")
@click.option("--fix-format", is_flag=True, help="Auto-fix formatting issues")
@click.option("--fix-lint", is_flag=True, help="Auto-fix linting issues")
@click.option("--fix-newlines", is_flag=True, help="Auto-fix trailing newlines")
@click.option("--skip-tests", is_flag=True, help="Skip running tests")
@click.pass_context
def check(
    ctx,
    fix_all: bool,
    fix_format: bool,
    fix_lint: bool,
    fix_newlines: bool,
    skip_tests: bool,
) -> None:
    """Run code quality checks (default: check only, no fixes)"""
    # If called without subcommand, run the actual check logic
    if ctx.invoked_subcommand is None:
        _run_checks(fix_all, fix_format, fix_lint, fix_newlines, skip_tests)


def _run_checks(
    fix_all: bool,
    fix_format: bool,
    fix_lint: bool,
    fix_newlines: bool,
    skip_tests: bool,
) -> None:
    """Internal function to run the actual checks."""
    console.print()

    # If --fix-all is used, enable all fix options
    if fix_all:
        fix_format = fix_lint = fix_newlines = True
        console.print("🔧 Running in full fix mode...", style="yellow")
        console.print()

    success = True

    # Formatter
    console.print("✨ Running formatter...", style="blue")
    if fix_format:
        success &= run_command(
            ["uv", "tool", "run", "ruff", "format", "src/", "tests/"], "Formatting"
        )
    else:
        success &= run_command(
            ["uv", "tool", "run", "ruff", "format", "src/", "tests/", "--check"],
            "Format check",
        )
    console.print()

    # Linter
    console.print("🔍 Running linter...", style="blue")
    if fix_lint:
        success &= run_command(
            ["uv", "tool", "run", "ruff", "check", "src/", "tests/", "--fix"],
            "Linting with fixes",
        )
    else:
        success &= run_command(
            ["uv", "tool", "run", "ruff", "check", "src/", "tests/"], "Linting"
        )
    console.print()

    # Type checker
    console.print("🔎 Running type checker...", style="blue")
    success &= run_command(["uv", "tool", "run", "mypy", "src/"], "Type checking")
    console.print()

    # Trailing newlines
    console.print("📄 Checking file endings...", style="blue")
    success &= check_trailing_newlines(fix_newlines)
    console.print()

    # Tests
    if not skip_tests:
        console.print("🧪 Running tests...", style="blue")
        success &= run_command(["uv", "run", "pytest"], "Tests")
        console.print()

    # Summary
    if fix_all or fix_format or fix_lint or fix_newlines:
        if success:
            console.print("🔧 All checks completed with fixes applied!", style="green")
        else:
            console.print("🔧 Some checks failed even with fixes applied", style="red")
    else:
        if success:
            console.print("✅ All checks passed!", style="green")
        else:
            console.print("❌ Some checks failed", style="red")

    console.print()

    if not success:
        sys.exit(1)


@check.command(name="fix-all")
@click.help_option("-h", "--help")
@click.option("--skip-tests", is_flag=True, help="Skip running tests")
def check_fix_all(skip_tests: bool) -> None:
    """Run checks with all fixes applied"""
    _run_checks(True, False, False, False, skip_tests)  # fix_all=True enables all fixes


@cli.command(name="fix-all")
@click.help_option("-h", "--help")
@click.option("--skip-tests", is_flag=True, help="Skip running tests")
def fix_all_command(skip_tests: bool) -> None:
    """Run all checks with auto-fixes applied"""
    _run_checks(True, False, False, False, skip_tests)  # fix_all=True enables all fixes


if __name__ == "__main__":
    cli()
