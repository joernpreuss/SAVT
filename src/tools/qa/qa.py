#!/usr/bin/env python3
"""SAVT Code Quality Checker"""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console(force_terminal=True)


# Command builders to avoid duplication and improve flexibility
def _code_format_cmd(check: bool = False) -> list[str]:
    """Build ruff format command."""
    cmd = ["uv", "tool", "run", "ruff", "format", "src/", "tests/"]
    if check:
        cmd.extend(["--check", "--diff"])
    return cmd


def _template_format_cmd(check: bool = False) -> list[str]:
    """Build djlint format command."""
    if check:
        return ["uv", "run", "djlint", "templates/"]
    return ["uv", "run", "djlint", "templates/", "--reformat"]


def _lint_cmd(fix: bool = False, unsafe: bool = False) -> list[str]:
    """Build ruff check command with optional fixes."""
    cmd = ["uv", "tool", "run", "ruff", "check", "src/", "tests/"]
    if fix:
        cmd.append("--fix")
        if unsafe:
            cmd.append("--unsafe-fixes")
    return cmd


def _typecheck_cmd() -> list[str]:
    """Build mypy command."""
    return ["uv", "tool", "run", "mypy", "src/"]


def _get_single_key() -> str:
    """Get a single keypress without requiring Enter."""
    try:
        # Windows
        import msvcrt  # type: ignore

        key_bytes: bytes = msvcrt.getch()  # type: ignore
        key: str = key_bytes.decode("utf-8")
        # Handle ESC key (ASCII 27)
        if ord(key[0]) == 27:
            return "q"  # Treat ESC as quit
        return key.lower()  # type: ignore
    except ImportError:
        try:
            # Unix/Linux/macOS
            import termios
            import tty

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)  # type: ignore
                key = sys.stdin.read(1)
                # Handle ESC key (ASCII 27)
                if ord(key) == 27:
                    return "q"  # Treat ESC as quit
                return key.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, OSError, termios.error):  # type: ignore
            # Fallback to regular input if terminal doesn't support raw mode
            return input().strip().lower()[:1] or "s"


def _prompt_fix_skip_quit(issue_type: str) -> str:
    """Prompt user for fix/skip/quit choice and handle the response."""
    if issue_type.lower() == "linting":
        console.print(
            f"{issue_type} issues found. Press: (f)ix, (u)nsafe fix, (s)kip, or (q)uit",
            style="yellow",
        )
    else:
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
    elif choice == "u" and issue_type.lower() == "linting":
        return "unsafe_fix"
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

    missing_files: list[str] = []

    # Check files with extensions
    for pattern in extensions:
        for file_path in Path(".").rglob(pattern):
            if any(part in exclude_dirs for part in file_path.parts):
                continue
            if file_path.is_file() and file_path.stat().st_size > 0:
                with open(file_path, "rb") as f:
                    f.seek(-1, 2)  # Go to last byte
                    if f.read(1) != b"\n":
                        missing_files.append(str(file_path))

    # Check specific root-level executable scripts
    root_executables = ["pytreqt", "qa"]
    for name in root_executables:
        file_path = Path(name)
        if file_path.is_file() and file_path.stat().st_size > 0:
            with open(file_path, "rb") as f:
                f.seek(-1, 2)  # Go to last byte
                if f.read(1) != b"\n":
                    missing_files.append(str(file_path))

    if missing_files:
        console.print("❌ Files missing trailing newlines:", style="red")
        for file_name in missing_files:
            console.print(f"  {file_name}", style="dim")

        if fix:
            for file_name in missing_files:
                with open(file_name, "a") as f:
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
      qa check --unsafe-fixes    - enable unsafe fixes for linting
      qa check --skip-tests      - skip test execution
      qa fix-all                 - shortcut for 'qa check --fix-all'

    Individual commands:
      qa format                  - run formatter (code + templates)
      qa lint                    - run linter only
      qa typecheck               - run type checker only
      qa newlines                - check/fix trailing newlines only
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
    unsafe_fixes: bool = typer.Option(
        False, "--unsafe-fixes", help="Enable unsafe fixes for linting"
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
    _run_checks(fix_all, fix_format, fix_lint, fix_newlines, unsafe_fixes, skip_tests)


def _show_requirements_coverage() -> None:
    """Show requirements coverage from last test run using pytreqt."""
    cmd = ["uv", "run", "python", "-m", "src.tools.pytreqt", "show"]
    _run_command(cmd, "Requirements coverage", show_output=True)


def _run_individual_check(check_type: str, exit_on_failure: bool = False) -> bool:
    """Run a specific check using existing logic."""
    success = False
    try:
        if check_type == "format":
            console.print("✨ Running formatter...", style="cyan")
            # Format code
            code_success = _run_command(_code_format_cmd(), "Code formatting")
            # Format templates
            template_success = _run_command(
                _template_format_cmd(), "Template formatting"
            )
            success = code_success and template_success
            if success:
                console.print("✅ Formatting completed", style="green")
            else:
                console.print("❌ Formatting failed", style="red")
        elif check_type == "lint":
            console.print("🔍 Running linter...", style="cyan")
            success = _run_command(_lint_cmd(), "Linting", show_output=True)
            if success:
                console.print("✅ No linting issues found", style="green")
            else:
                console.print("❌ Linting issues found", style="red")
        elif check_type == "typecheck":
            console.print("🔎 Running type checker...", style="cyan")
            success = _run_command(_typecheck_cmd(), "Type checking")
            if success:
                console.print("✅ Type checking passed", style="green")
            else:
                console.print("❌ Type checking failed", style="red")
        elif check_type == "newlines":
            console.print("📄 Checking file endings...", style="cyan")
            success = _check_trailing_newlines(False)
            if success:
                console.print(
                    "✅ All files have proper trailing newlines", style="green"
                )
            else:
                console.print("❌ Trailing newline issues found", style="red")
    except Exception:
        # Continue the interactive loop on any error
        success = False

    if exit_on_failure and not success:
        sys.exit(1)

    return success


def _interactive_menu(success: bool = True, title: str = "🧪 Test Selection") -> bool:
    """Run the interactive menu for test selection and individual checks."""
    selected_db = "sqlite"  # Default database

    # Mapping of choice to parallel workers (Fibonacci sequence)
    parallel_workers = {
        "1": 1,  # Single-threaded
        "2": 2,
        "3": 3,
        "4": 5,
        "5": 8,
        "6": 13,
        "7": 21,
        "8": 34,
        "9": 55,
        "0": 89,
        "x": 120,
        "y": 160,
        "z": 200,
    }

    while True:
        console.print(title, style="cyan")
        console.print(f"Current database: [bold]{selected_db.upper()}[/bold]")
        console.print()

        console.print("  (h) - Show help/options")
        console.print("  (q) - Quit (or press ESC)")
        console.print()

        choice = _prompt_single_key("Select action", [], "1")

        if choice == "h":
            # Show help once, then continue with next iteration
            console.print()
            console.print("Available Options:", style="bold green")
            console.print("  (s) - Select SQLite database")
            console.print("  (p) - Select PostgreSQL database")
            console.print()
            console.print("  Rerun individual checks:")
            console.print("  (f) - Run formatter (code + templates)")
            console.print("  (l) - Run linter")
            console.print("  (t) - Run type checker")
            console.print("  (n) - Run newlines check")
            console.print("  (a) - Run all checks")
            console.print()
            console.print("  Run tests with parallel workers:")
            for key, workers in parallel_workers.items():
                if workers == 1:
                    console.print(
                        f"  ({key}) - Run with {workers} worker (single-threaded)"
                    )
                else:
                    console.print(f"  ({key}) - Run with {workers} parallel workers")
            console.print()
            console.print("  (r) - View requirements coverage")
            console.print("  (c) - Clear screen")
            console.print("  (q) - Quit (or press ESC)")
            console.print()
            continue  # Go back to menu without changing show_options
        elif choice in ["s", "sqlite"]:
            selected_db = "sqlite"
            console.print("✅ Selected SQLite database", style="green")
        elif choice in ["p", "postgresql"]:
            selected_db = "postgresql"
            console.print("✅ Selected PostgreSQL database", style="green")
        elif choice == "f":
            _run_individual_check("format")
        elif choice == "l":
            _run_individual_check("lint")
        elif choice == "t":
            _run_individual_check("typecheck")
        elif choice == "n":
            _run_individual_check("newlines")
        elif choice == "a":
            console.print("🔄 Rerunning all checks...", style="cyan")
            # Recursively call the function with same parameters
            _run_checks(
                False, False, False, False, False, True
            )  # skip_tests=True to avoid double test menu
        elif choice in parallel_workers:
            parallel = parallel_workers[choice]
            if parallel == 1:
                test_success = _run_database_tests(
                    selected_db
                )  # Single-threaded, no -n flag
            else:
                test_success = _run_database_tests(selected_db, parallel=parallel)
            success &= test_success
        elif choice in ["r", "requirements"]:
            _show_requirements_coverage()
        elif choice in ["c", "clear"]:
            # Clear screen using ANSI escape sequence
            import os

            os.system("cls" if os.name == "nt" else "clear")
            continue
        elif choice in ["q", "quit"]:
            if title == "🧪 Test Selection":
                console.print("Skipping tests.", style="yellow")
            else:
                console.print("Exiting interactive mode.", style="yellow")
            break
        else:
            console.print(
                "Please enter valid option: h/q (press 'h' for help)",
                style="yellow",
            )
            continue

        # Continue the loop
        console.print()

    return success


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
    unsafe_fixes: bool,
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
    interactive_fixes: list[str] = []
    had_issues = False

    # Formatter (includes code and templates)
    console.print("✨ Running formatter...", style="cyan")
    if fix_format:
        # Format code
        code_success = _run_command(_code_format_cmd(), "Code formatting")
        # Format templates
        template_success = _run_command(_template_format_cmd(), "Template formatting")
        success &= code_success and template_success
    else:
        # Check code formatting
        code_format_result = _run_command(
            _code_format_cmd(check=True), "Code format check", show_output=True
        )
        # Check template formatting
        template_format_result = _run_command(
            _template_format_cmd(check=True), "Template format check", show_output=True
        )

        format_result = code_format_result and template_format_result
        success &= format_result

        if not format_result:
            had_issues = True
            choice = _prompt_fix_skip_quit("Formatting")
            if choice == "fix":
                _run_command(_code_format_cmd(), "Code formatting")
                _run_command(_template_format_cmd(), "Template formatting")
                interactive_fixes.append("format")
        else:
            console.print("✅ No formatting issues found", style="green")
    console.print()

    # Linter
    console.print("🔍 Running linter...", style="cyan")
    if fix_lint:
        success &= _run_command(
            _lint_cmd(fix=True, unsafe=unsafe_fixes), "Linting with fixes"
        )
    else:
        lint_result = _run_command(_lint_cmd(), "Linting", show_output=True)
        success &= lint_result
        if not lint_result:
            had_issues = True
            choice = _prompt_fix_skip_quit("Linting")
            if choice in ["fix", "unsafe_fix"]:
                use_unsafe = unsafe_fixes or choice == "unsafe_fix"
                lint_cmd = _lint_cmd(fix=True, unsafe=use_unsafe)

                fix_type = "unsafe fixes" if use_unsafe else "fixes"
                _run_command(lint_cmd, f"Linting with {fix_type}")
                interactive_fixes.append("lint")

                # Check if issues remain after fix attempt
                recheck_result = _run_command(
                    _lint_cmd(), "Re-checking linting", show_output=True
                )

                # If issues still exist, offer unsafe fix option again
                if not recheck_result and choice != "unsafe_fix":
                    console.print(
                        "Issues still remain after fix attempt.", style="yellow"
                    )
                    retry_choice = _prompt_fix_skip_quit("Linting")
                    if retry_choice == "unsafe_fix":
                        _run_command(
                            _lint_cmd(fix=True, unsafe=True),
                            "Linting with unsafe fixes",
                        )
                        interactive_fixes.append("lint-unsafe")
        else:
            console.print("✅ No linting issues found", style="green")
    console.print()

    # Type checker
    console.print("🔎 Running type checker...", style="cyan")
    success &= _run_command(_typecheck_cmd(), "Type checking")
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
        success = _interactive_menu(success)

    # Summary and interactive rerun options
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
    _run_checks(
        True, False, False, False, False, skip_tests
    )  # fix_all=True enables all fixes


@app.command("format")
def format_command(
    ctx: typer.Context,
    check_only: bool = typer.Option(
        False, "--check", help="Check formatting without fixing"
    ),
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Run formatter (ruff format + djlint)"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    if check_only:
        console.print("✨ Running formatter...", style="cyan")
        # Check code formatting
        code_success = _run_command(
            _code_format_cmd(check=True), "Code format check", show_output=True
        )
        # Check template formatting
        template_success = _run_command(
            _template_format_cmd(check=True), "Template format check", show_output=True
        )

        success = code_success and template_success
        if success:
            console.print("✅ No formatting issues found", style="green")
        else:
            console.print("❌ Formatting issues found", style="red")
            sys.exit(1)
    else:
        _run_individual_check("format", exit_on_failure=True)


@app.command("lint")
def lint_command(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Fix linting issues"),
    unsafe_fixes: bool = typer.Option(
        False, "--unsafe-fixes", help="Enable unsafe fixes"
    ),
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Run linter (ruff check)"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    if fix:
        console.print("🔍 Running linter...", style="cyan")
        cmd = _lint_cmd(fix=fix, unsafe=unsafe_fixes)
        success = _run_command(cmd, "Linting", show_output=True)

        if success:
            console.print("✅ No linting issues found", style="green")
        else:
            console.print("❌ Some linting issues could not be fixed", style="red")
            sys.exit(1)
    else:
        _run_individual_check("lint", exit_on_failure=True)


@app.command("typecheck")
def typecheck_command(
    ctx: typer.Context,
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Run type checker (mypy)"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _run_individual_check("typecheck", exit_on_failure=True)


@app.command("newlines")
def newlines_command(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Fix trailing newline issues"),
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Check/fix trailing newlines in files"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    if fix:
        console.print("📄 Checking file endings...", style="cyan")
        success = _check_trailing_newlines(fix)

        if success:
            console.print("✅ All files have proper trailing newlines", style="green")
        else:
            console.print("❌ Failed to fix trailing newline issues", style="red")
            sys.exit(1)
    else:
        _run_individual_check("newlines", exit_on_failure=True)


@app.command("i")
def interactive(
    ctx: typer.Context,
    help_flag: bool = typer.Option(
        False, "-h", "--help", help="Show this message and exit"
    ),
) -> None:
    """Interactive mode - shows options menu without running anything initially"""
    if help_flag:
        typer.echo(ctx.get_help())
        raise typer.Exit()

    _interactive_menu(title="🔧 Interactive QA Mode")


if __name__ == "__main__":
    app()
