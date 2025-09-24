"""Nox configuration for SAVT quality assurance tasks."""

import nox

# Python versions to test (SAVT uses Python 3.13)
PYTHON_VERSIONS = ["3.13"]


@nox.session(python=PYTHON_VERSIONS)
def lint(session: nox.Session) -> None:
    """Run linting with ruff check."""
    session.install("-e", ".[dev]")
    session.run("uv", "tool", "run", "ruff", "check", "src/", "tests/")


@nox.session(python=PYTHON_VERSIONS)
def mypy(session: nox.Session) -> None:
    """Run type checking with mypy."""
    session.install("-e", ".[dev]")
    session.run("uv", "tool", "run", "mypy", "src/", "tests/")


@nox.session(python=PYTHON_VERSIONS)
def format_check(session: nox.Session) -> None:
    """Check code formatting with ruff format."""
    session.install("-e", ".[dev]")
    session.run(
        "uv", "tool", "run", "ruff", "format", "src/", "tests/", "--check", "--diff"
    )


@nox.session
def format(session: nox.Session) -> None:
    """Format code with ruff format."""
    session.install("-e", ".[dev]")
    session.run("uv", "tool", "run", "ruff", "format", "src/", "tests/")


@nox.session
def djlint_check(session: nox.Session) -> None:
    """Check HTML template formatting with djlint."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "djlint", "templates/")


@nox.session
def djlint_format(session: nox.Session) -> None:
    """Format HTML templates with djlint."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "djlint", "templates/", "--reformat")


@nox.session
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


@nox.session
def qa(session: nox.Session) -> None:
    """Run all QA checks (no fixes)."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "qa", "check")


@nox.session
def qa_fix(session: nox.Session) -> None:
    """Run all QA checks with fixes."""
    session.install("-e", ".[dev]")
    session.run("uv", "run", "qa", "check", "--fix-all")
