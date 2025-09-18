#!/usr/bin/env python3
"""SAVT Code Quality Checker"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console(force_terminal=True)


def _get_single_key() -> str:
    """Get a single keypress without requiring Enter."""
    try:
        # Windows
        import msvcrt  # type: ignore

        key_bytes = msvcrt.getch()  # type: ignore
        return key_bytes.decode("utf-8").lower()  # type: ignore
    except ImportError:
        try:
            # Unix/Linux/macOS
            import sys
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)  # type: ignore
                return sys.stdin.read(1).lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, OSError, termios.error):  # type: ignore
            # Fallback to regular input if terminal doesn't support raw mode
            return input().strip().lower()[:1] or "s"


def _prompt_fix_skip_quit(issue_type: str) -> str:
    """Prompt user for fix/skip/quit choice and handle the response."""
    console.print(
        f"{issue_type} issues found. Press: (f)ix, (s)kip, or (q)uit",
        style="yellow",
    )
    choice = _get_single_key()
    console.print(f"[{choice}]")

    if choice == "q":
        console.print("Exiting QA check.", style="yellow")
        sys.exit(0)
    elif choice == "f":
        return "fix"
    return "skip"


def _prompt_single_key(message: str, options: list[str], default: str = "") -> str:
    """Prompt user for single keypress choice."""
    console.print(f"{message} ({'/'.join(options)})", style="cyan")
    if default:
        console.print(f"Press key or Enter for default [{default}]:", style="dim")
    else:
        console.print("Press key:", style="dim")

    choice = _get_single_key()

    # Handle Enter key (returns empty string or newline)
    if choice in ["", "\n", "\r"] and default:
        choice = default

    console.print(f"[{choice}]")
    return choice.lower().strip()


def _run_command(cmd: list[str], description: str, show_output: bool = False) -> bool:
    """Run a command and return success status."""
    try:
        if show_output:
            # Let output go directly to terminal to preserve colors
            result = subprocess.run(cmd, check=True, text=True)
        else:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        console.print(f"❌ {description} failed", style="red")
        if show_output:
            # Output was already shown during execution
            pass
        else:
            # Show captured output
            if e.stdout:
                print(e.stdout, end="")
            if e.stderr:
                print(e.stderr, end="")
        return False


def _check_trailing_newlines(fix: bool = False) -> bool:
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
        return True


app = typer.Typer(
    name="qa",
    help="""SAVT Quality Assurance Tool

    Examples:
      qa check                   - run all checks (no fixes)
      qa check --fix-all         - run checks with all fixes
      qa check --fix-format      - fix formatting only
      qa check --fix-lint        - fix linting only
      qa check --fix-newlines    - fix newlines only
      qa check --skip-tests      - skip test execution
      qa fix-all                 - shortcut for 'qa check --fix-all'
    """,
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def main():
    """Main entry point for the QA tool."""
    app()


@app.command()
def check(
    ctx: typer.Context,
    fix_all: bool = typer.Option(False, "--fix-all", help="Auto-fix all issues"),
    fix_format: bool = typer.Option(
        False, "--fix-format", help="Auto-fix formatting issues"
    ),
    fix_lint: bool = typer.Option(False, "--fix-lint", help="Auto-fix linting issues"),
    fix_newlines: bool = typer.Option(
        False, "--fix-newlines", help="Auto-fix trailing newlines"
    ),
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip running tests"),
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Run code quality checks (default: check only, no fixes)"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _run_checks(fix_all, fix_format, fix_lint, fix_newlines, skip_tests)


def _show_requirements_coverage() -> None:
    """Show requirements coverage from last test run."""
    import json
    from pathlib import Path

    console.print("📋 Showing requirements coverage from last run...", style="cyan")

    cache_file = Path(".pytest_cache") / "requirements_coverage.json"
    if not cache_file.exists():
        console.print(
            "❌ No cached requirements coverage found. Run tests first.", style="red"
        )
        return

    try:
        with open(cache_file, encoding="utf-8") as f:
            coverage_data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"❌ Error reading cached coverage: {e}", style="red")
        return

    console.print("Requirements Coverage (Last Run)", style="green")
    console.print()

    # Show command info
    command_info = coverage_data.get("command_info", {})
    if command_info:
        console.print(
            f"Database: {command_info.get('database', 'unknown')}", style="dim"
        )
        console.print(
            f"Generated: {command_info.get('timestamp', 'unknown')}", style="dim"
        )
        console.print(f"Command: {command_info.get('command', 'unknown')}", style="dim")

        git_info = command_info.get("git", {})
        if "error" not in git_info and git_info:
            branch = git_info.get("branch", "unknown")
            commit_short = git_info.get("commit_short", "unknown")
            clean_status = "clean" if git_info.get("clean", False) else "dirty"
            console.print(f"Git: {branch}@{commit_short} ({clean_status})", style="dim")

        env_vars = command_info.get("environment_variables", {})
        if env_vars:
            env_str = ", ".join(f"{k}={v}" for k, v in env_vars.items())
            console.print(f"Environment: {env_str}", style="dim")

        console.print()

    # Display requirements and their tests
    for req in sorted(coverage_data["requirements"].keys()):
        tests = coverage_data["requirements"][req]
        console.print(f"  {req}:", style="white")

        for test_info in tests:
            result = test_info["result"]
            if result == "passed":
                symbol = "✓"
                color = "green"
            elif result == "failed":
                symbol = "✗"
                color = "red"
            elif result == "skipped":
                symbol = "⊝"
                color = "yellow"
            else:
                symbol = "?"
                color = "purple"

            console.print(f"    {symbol} {test_info['test_name']}", style=color)

    # Summary statistics
    summary = coverage_data["summary"]
    console.print()
    console.print("Requirements Coverage Summary:", style="cyan")
    console.print(f"  Tests with requirements: {summary['total_tests']}")
    console.print(f"  Requirements covered: {summary['total_requirements']}")


def _run_database_tests(db_type: str, parallel: int = 1) -> bool:
    """Run database tests."""
    if db_type == "sqlite":
        cmd = ["uv", "run", "pytest", "--color=yes"]
        if parallel > 1:
            cmd.extend(["-n", str(parallel)])
            description = f"SQLite Tests (-n{parallel})"
        else:
            description = "SQLite Tests"
        emoji = "🧪"
    else:  # postgresql
        cmd = [
            "env",
            "TEST_DATABASE=postgresql",
            "DATABASE_URL=postgresql://savt_user:savt_password@localhost:5432/savt",
            "uv",
            "run",
            "pytest",
            "--color=yes",
        ]
        if parallel > 1:
            cmd.extend(["-n", str(parallel)])
            description = f"PostgreSQL Tests (-n{parallel})"
        else:
            description = "PostgreSQL Tests"
        emoji = "🐘"

    console.print(f"{emoji} Running {description}...", style="cyan")
    test_success = _run_command(cmd, description, show_output=True)

    if test_success:
        console.print(f"✅ {description} passed!", style="green")
    else:
        console.print(f"❌ {description} failed", style="red")

    return test_success


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
    interactive_fixes = []
    had_issues = False

    # Formatter
    console.print("✨ Running formatter...", style="cyan")
    if fix_format:
        success &= _run_command(
            ["uv", "tool", "run", "ruff", "format", "src/", "tests/"], "Formatting"
        )
    else:
        format_result = _run_command(
            [
                "uv",
                "tool",
                "run",
                "ruff",
                "format",
                "src/",
                "tests/",
                "--check",
                "--diff",
            ],
            "Format check",
            show_output=True,
        )
        success &= format_result
        if not format_result:
            had_issues = True
            choice = _prompt_fix_skip_quit("Formatting")
            if choice == "fix":
                _run_command(
                    ["uv", "tool", "run", "ruff", "format", "src/", "tests/"],
                    "Formatting",
                )
                interactive_fixes.append("format")
        else:
            console.print("✅ No formatting issues found", style="green")
    console.print()

    # Linter
    console.print("🔍 Running linter...", style="cyan")
    if fix_lint:
        success &= _run_command(
            ["uv", "tool", "run", "ruff", "check", "src/", "tests/", "--fix"],
            "Linting with fixes",
        )
    else:
        lint_result = _run_command(
            ["uv", "tool", "run", "ruff", "check", "src/", "tests/"],
            "Linting",
            show_output=True,
        )
        success &= lint_result
        if not lint_result:
            had_issues = True
            choice = _prompt_fix_skip_quit("Linting")
            if choice == "fix":
                _run_command(
                    ["uv", "tool", "run", "ruff", "check", "src/", "tests/", "--fix"],
                    "Linting with fixes",
                )
                interactive_fixes.append("lint")
        else:
            console.print("✅ No linting issues found", style="green")
    console.print()

    # Template formatter/linter
    console.print("🎨 Running template formatter...", style="cyan")
    if fix_format:
        success &= _run_command(
            ["uv", "run", "djlint", "templates/", "--reformat"],
            "Template formatting",
        )
    else:
        template_success = _run_command(
            ["uv", "run", "djlint", "templates/"],
            "Template linting",
            show_output=True,
        )
        if not template_success and not (fix_all or fix_format):
            had_issues = True
            choice = _prompt_fix_skip_quit("Template")
            if choice == "fix":
                console.print("🔧 Fixing template issues...", style="yellow")
                success &= _run_command(
                    ["uv", "run", "djlint", "templates/", "--reformat"],
                    "Template formatting",
                )
                interactive_fixes.append("template")
        else:
            success &= template_success
    console.print()

    # Type checker
    console.print("🔎 Running type checker...", style="cyan")
    success &= _run_command(["uv", "tool", "run", "mypy", "src/"], "Type checking")
    console.print()

    # Trailing newlines
    console.print("📄 Checking file endings...", style="cyan")
    if fix_newlines:
        success &= _check_trailing_newlines(fix_newlines)
    else:
        newlines_result = _check_trailing_newlines(fix_newlines)
        success &= newlines_result
        if not newlines_result:
            had_issues = True
            choice = _prompt_fix_skip_quit("Trailing newline")
            if choice == "fix":
                _check_trailing_newlines(True)
                interactive_fixes.append("newlines")
        else:
            console.print("✅ All files have proper trailing newlines", style="green")
    console.print()

    # Tests - Interactive database selection and test execution
    if not skip_tests:
        selected_db = "sqlite"  # Default database

        while True:
            console.print("🧪 Test Selection", style="cyan")
            console.print(f"Current database: [bold]{selected_db.upper()}[/bold]")
            console.print()

            # Show available commands
            console.print("📋 SQLite command: [dim]uv run pytest --color=yes[/dim]")
            psql_cmd = (
                "TEST_DATABASE=postgresql DATABASE_URL="
                "postgresql://savt_user:savt_password@localhost:5432/savt "
                "uv run pytest --color=yes"
            )
            console.print(f"📋 PostgreSQL command: [dim]{psql_cmd}[/dim]")
            req_cmd = "uv run pytest --requirements-report -q"
            console.print(f"📋 Requirements command: [dim]{req_cmd}[/dim]")
            console.print()

            console.print("Options:", style="bold")
            console.print("  (s) - Select SQLite database")
            console.print("  (p) - Select PostgreSQL database")
            console.print()
            console.print("  Run tests with parallel workers:")
            console.print("  (1) - Run with 1 worker (single-threaded)")
            console.print("  (2) - Run with 2 parallel workers")
            console.print("  (3) - Run with 3 parallel workers")
            console.print("  (4) - Run with 5 parallel workers")
            console.print("  (5) - Run with 8 parallel workers")
            console.print("  (6) - Run with 13 parallel workers")
            console.print("  (7) - Run with 21 parallel workers")
            console.print("  (8) - Run with 34 parallel workers")
            console.print("  (9) - Run with 55 parallel workers")
            console.print("  (0) - Run with 89 parallel workers")
            console.print()
            console.print("  (r) - View requirements coverage")
            console.print("  (q) - Quit")
            console.print()

            choice = _prompt_single_key("Select action", [], "1")

            if choice in ["s", "sqlite"]:
                selected_db = "sqlite"
                console.print("✅ Selected SQLite database", style="green")
            elif choice in ["p", "postgresql"]:
                selected_db = "postgresql"
                console.print("✅ Selected PostgreSQL database", style="green")
            elif choice == "1":
                test_success = _run_database_tests(
                    selected_db
                )  # Single-threaded, no -n flag
                success &= test_success
            elif choice == "2":
                test_success = _run_database_tests(selected_db, parallel=2)
                success &= test_success
            elif choice == "3":
                test_success = _run_database_tests(selected_db, parallel=3)
                success &= test_success
            elif choice == "4":
                test_success = _run_database_tests(selected_db, parallel=5)
                success &= test_success
            elif choice == "5":
                test_success = _run_database_tests(selected_db, parallel=8)
                success &= test_success
            elif choice == "6":
                test_success = _run_database_tests(selected_db, parallel=13)
                success &= test_success
            elif choice == "7":
                test_success = _run_database_tests(selected_db, parallel=21)
                success &= test_success
            elif choice == "8":
                test_success = _run_database_tests(selected_db, parallel=34)
                success &= test_success
            elif choice == "9":
                test_success = _run_database_tests(selected_db, parallel=55)
                success &= test_success
            elif choice == "0":
                test_success = _run_database_tests(selected_db, parallel=89)
                success &= test_success
            elif choice in ["r", "requirements"]:
                _show_requirements_coverage()
            elif choice in ["q", "quit"]:
                console.print("Skipping tests.", style="yellow")
                break
            else:
                console.print(
                    "Please enter valid option: s/p/0-9/r/q",
                    style="yellow",
                )
                continue

            # Continue the loop
            console.print()

    # Summary
    if fix_all or fix_format or fix_lint or fix_newlines:
        if success:
            console.print("🔧 All checks completed with fixes applied!", style="green")
        else:
            console.print("🔧 Some checks failed even with fixes applied", style="red")
    else:
        # If we had issues but applied interactive fixes, consider it a success
        if success or (had_issues and interactive_fixes):
            if interactive_fixes:
                console.print(
                    "✅ All checks passed after applying fixes!", style="green"
                )
            else:
                console.print("✅ All checks passed!", style="green")
        else:
            console.print("❌ Some checks failed", style="red")

    if interactive_fixes:
        console.print(
            f"🔧 Applied fixes: {', '.join(interactive_fixes)}", style="green"
        )

    console.print()

    # Exit with error only if we truly failed (no fixes applied or fixes didn't work)
    if not success and not (had_issues and interactive_fixes):
        sys.exit(1)


@app.command("fix-all")
def fix_all_command(
    ctx: typer.Context,
    skip_tests: bool = typer.Option(False, "--skip-tests", help="Skip running tests"),
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Run all checks with auto-fixes applied"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()
    _run_checks(True, False, False, False, skip_tests)  # fix_all=True enables all fixes


if __name__ == "__main__":
    app()
