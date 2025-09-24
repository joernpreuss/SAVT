"""Nox configuration for SAVT quality assurance tasks."""

import nox  # pyright: ignore[reportMissingImports] # noqa: I001

# Configure nox to use uv for faster package installs
nox.options.default_venv_backend = "uv"

# Python versions to test (SAVT uses Python 3.13)
PYTHON_VERSIONS = ["3.13"]

# Centralized tool configurations for sharing with qa.py
LINT_TOOL = ["uv", "tool", "run", "ruff", "check"]
LINT_PATHS = ["src/", "tests/"]
FORMAT_TOOL = ["uv", "tool", "run", "ruff", "format"]
FORMAT_PATHS = ["src/", "tests/"]
TYPECHECK_TOOL = ["uv", "tool", "run", "mypy"]
TYPECHECK_PATHS = ["src/", "tests/"]
DJLINT_TOOL = ["uv", "run", "djlint"]
DJLINT_PATHS = ["templates/"]

def get_lint_command(
    fix: bool = False, unsafe: bool = False, path: str = "."
) -> list[str]:
    """Get lint command for external use."""
    paths = [f"{path}/{p}" if path != "." else p for p in LINT_PATHS]
    cmd = LINT_TOOL + paths
    if fix:
        cmd.append("--fix")
        if unsafe:
            cmd.append("--unsafe-fixes")
    return cmd


def get_format_command(check: bool = False, path: str = ".") -> list[str]:
    """Get format command for external use."""
    paths = [f"{path}/{p}" if path != "." else p for p in FORMAT_PATHS]
    cmd = FORMAT_TOOL + paths
    if check:
        cmd.extend(["--check", "--diff"])
    return cmd


def get_typecheck_command(path: str = ".") -> list[str]:
    """Get typecheck command for external use."""
    paths = [f"{path}/{p}" if path != "." else p for p in TYPECHECK_PATHS]
    return TYPECHECK_TOOL + paths


def get_djlint_command(check: bool = False, path: str = ".") -> list[str]:
    """Get djlint command for external use."""
    paths = [f"{path}/{p}" if path != "." else p for p in DJLINT_PATHS]
    cmd = DJLINT_TOOL + paths
    if not check:
        cmd.append("--reformat")
    return cmd


@nox.session(python=PYTHON_VERSIONS)
def lint(session: nox.Session) -> None:
    """Run linting with ruff check."""
    session.install("-e", ".[dev]")
    session.run(*get_lint_command(), external=True)


@nox.session(python=PYTHON_VERSIONS)
def mypy(session: nox.Session) -> None:
    """Run type checking with mypy."""
    session.install("-e", ".[dev]")
    session.run(*get_typecheck_command(), external=True)


@nox.session(python=PYTHON_VERSIONS)
def format_check(session: nox.Session) -> None:
    """Check code formatting with ruff format."""
    session.install("-e", ".[dev]")
    session.run(*get_format_command(check=True), external=True)


@nox.session(python=PYTHON_VERSIONS)
def format(session: nox.Session) -> None:
    """Format code with ruff format."""
    session.install("-e", ".[dev]")
    session.run(*get_format_command(), external=True)


@nox.session(python=PYTHON_VERSIONS)
def djlint_check(session: nox.Session) -> None:
    """Check HTML template formatting with djlint."""
    session.install("-e", ".[dev]")
    session.run(*get_djlint_command(check=True), external=True)


@nox.session(python=PYTHON_VERSIONS)
def djlint_format(session: nox.Session) -> None:
    """Format HTML templates with djlint."""
    session.install("-e", ".[dev]")
    session.run(*get_djlint_command(), external=True)


@nox.session(python=PYTHON_VERSIONS)
def newlines(session: nox.Session) -> None:
    """Check trailing newlines in files."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "qa", "newlines")


@nox.session(python=PYTHON_VERSIONS)
def tests(session: nox.Session) -> None:
    """Run tests with pytest (SQLite by default)."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "pytest", "--verbose")


@nox.session(python=PYTHON_VERSIONS)
def tests_postgres(session: nox.Session) -> None:
    """Run tests with PostgreSQL."""
    session.install("-e", ".[dev]")
    session.env["DATABASE_URL"] = (
        "postgresql://savt_user:savt_password@localhost:5432/savt"
    )
    session.run("uv", "run", "pytest", "--verbose")


@nox.session(python=PYTHON_VERSIONS)
def qa(session: nox.Session) -> None:
    """Run all QA checks (no fixes)."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "qa", "check")


@nox.session(python=PYTHON_VERSIONS)
def qa_fix(session: nox.Session) -> None:
    """Run all QA checks with fixes."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "qa", "check", "--fix-all")
