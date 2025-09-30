# SAVT

**Pure Python Suggestion And Veto Tool** - A collaborative decision-making platform built with modern Python tooling and clean architecture.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/badge/uv-package%20manager-orange.svg)](https://github.com/astral-sh/uv)

> **Note**: This project serves as an experiment in AI-assisted development, exploring deliberate architectural choices including pure Python with no JavaScript/TypeScript, server-side HTML with HTMX for dynamic interactions, modern tooling (uv, type hints), and comprehensive requirements traceability.

## Overview

SAVT is a collaborative decision-making platform that enables democratic consensus-building through a suggestion and veto model. Perfect for any group decision scenario—from social planning to business workflows.

**Core Features:**
- **Democratic suggestions** - Anyone can propose options
- **Veto-based consensus** - Participants can block options they strongly oppose
- **Flexible data model** - Configurable terminology for any use case
- **Real-time updates** - HTMX-powered interactions without JavaScript
- **Requirements traceability** - Novel system linking tests to functional requirements

**Use Cases:**
- Business decisions (vendor selection, budget allocation, policy changes)
- Development workflows (code reviews, deployments, architecture choices)
- Team coordination (meeting scheduling, project priorities, resource allocation)
- Social planning (restaurant choices, event planning, group activities)

## Architecture Highlights

**Clean Architecture with Domain-Driven Design:**
- **Domain Layer** (`src/domain/`) - Pure business entities with zero dependencies
- **Application Layer** (`src/application/`) - Business logic and service orchestration
- **Infrastructure Layer** (`src/infrastructure/`) - Database persistence with SQLModel
- **Presentation Layer** (`src/presentation/`) - FastAPI routes (HTML + JSON API)

**Technical Stack:**
- **FastAPI + SQLModel** - Modern async Python with type-safe ORM
- **Jinja2 + HTMX** - Server-side rendering with SPA-like interactions (zero JavaScript)
- **PostgreSQL/SQLite** - Dual database support (SQLite for dev, PostgreSQL for production)
- **pytest + structlog** - Comprehensive testing with structured logging
- **uv** - Lightning-fast package management (replaces pip, virtualenv, pyenv)

**Key Design Decisions:**
- Feature IDs for unique identification (allows duplicate names)
- Independent veto/unveto operations per user per feature
- No JavaScript - all interactivity via HTMX + server-side logic
- API versioning (`/api/v1/`) for forward compatibility
- Comprehensive OpenAPI documentation

## Quick Start

### Prerequisites

- **Python 3.13+** (pinned via `.python-version`)
- **uv** - Install: `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd SAVT

# Install dependencies
uv sync

# Start development server
uv run uvicorn src.main:app --reload --host 0.0.0.0
```

Access at: http://localhost:8000

### Configuration

Configure terminology for your use case:

```bash
# Pizza ordering example
cp .env.pizza .env

# Or customize in .env:
APP_NAME="My Voting Tool"
OBJECT_NAME_SINGULAR="item"        # Auto-pluralizes to "items"
PROPERTY_NAME_SINGULAR="feature"   # Auto-pluralizes to "features"
```

Override for irregular plurals:
```bash
OBJECT_NAME_SINGULAR="category"
OBJECT_NAME_PLURAL="categories"    # Override "categorys"
```

## Development

### Commands

**Quality Assurance:**
```bash
uv run qa check              # Interactive QA with rerun options
uv run qa check --fix-all    # Auto-fix all issues
uv run qa format             # Format code + templates (ruff + djlint)
uv run qa lint               # Lint code
uv run qa typecheck          # Type checking (mypy)
uv run qa newlines           # Check file endings
```

**Testing:**
```bash
# Fast tests (in-memory SQLite)
uv run pytest                # Run all tests
uv run pytest -n10           # Parallel execution
uv run pytest -v             # Verbose with requirements coverage

# PostgreSQL integration tests
TEST_DATABASE=postgresql DATABASE_URL=postgresql://user:pass@localhost:5432/savt uv run pytest

# Requirements traceability
uv run pytest --show-docstrings      # Display requirements during execution
uv run pytest --requirements-report  # Coverage report without running tests
```

**Server:**
```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0
```

### Database Setup

**SQLite (Default)** - Zero configuration, works out of the box.

**PostgreSQL (Production):**
```bash
# Quick setup with Docker
./scripts/postgres.sh setup

# Management commands
./scripts/postgres.sh start      # Start container
./scripts/postgres.sh status     # Check health
./scripts/postgres.sh shell      # psql console
./scripts/postgres.sh reset      # Reset database (DELETES DATA)
```

See [POSTGRESQL.md](./POSTGRESQL.md) for detailed setup.

### Project Structure

```
src/
├── domain/              # Pure business entities (zero dependencies)
│   ├── entities.py      # Domain models (dataclasses)
│   ├── constants.py     # Business constants
│   └── exceptions.py    # Domain exceptions
├── application/         # Business logic layer
│   ├── item_service.py              # Item CRUD
│   ├── feature_service.py           # Feature + veto logic
│   └── item_operations_service.py   # Complex operations (merge/split)
├── infrastructure/      # External concerns
│   └── database/
│       ├── models.py    # SQLModel persistence
│       └── db.py        # Connection management
├── presentation/        # API layer
│   ├── routes.py        # HTML routes
│   └── api_routes.py    # JSON API (OpenAPI docs)
└── main.py              # FastAPI application

templates/               # Jinja2 templates
├── *.html               # Page templates
├── fragments/           # HTMX partial updates
└── macros.html          # Reusable components

tests/                   # Comprehensive test suite
├── test_api.py          # API endpoint tests
├── test_service.py      # Business logic tests
└── conftest.py          # pytest fixtures
```

## Requirements Traceability System

**Novel approach** to linking tests with functional requirements—practical for everyday development without heavy enterprise tools.

### How It Works

Tests reference requirements in docstrings:

```python
def test_create_property_conflict(session: Session):
    """Test property name uniqueness enforcement.

    Covers:
    - FR-2.3: Property names must be unique within their scope
    - FR-2.4: System prevents duplicate property creation (409 error)
    """
    # Test implementation...
```

### Features

- Automatic extraction from docstrings (`FR-X.Y`, `BR-X.Y` patterns)
- Real-time coverage reporting during test execution
- Git-friendly (embedded in code, no external databases)
- Seamless pytest integration

### Usage

```bash
# Show requirements during test run
uv run pytest --show-docstrings

# Generate coverage report
uv run pytest -v

# Coverage analysis without running tests
uv run pytest --requirements-report -q
```

**Sample Output:**
```
Requirements Coverage
  FR-1.1:
    ✓ test_create_object_with_property
  FR-2.3:
    ✓ test_create_property_conflict
  BR-3.3:
    ✓ test_veto_idempotency
    ✓ test_unveto_idempotency

Requirements Coverage Summary:
  Tests with requirements: 12
  Requirements covered: 15
```

## Logging System

Structured logging with `structlog` for development and production:

**Development** - Rich console output with syntax highlighting
**Production** - JSON logs to `logs/savt.log` + console

### Log Types

- **API Requests:** `GET /api/endpoint - 200 (15.2ms)`
- **User Actions:** `User action: veto_property by anonymous`
- **Database Operations:** `Database create on SVObject succeeded`
- **System Events:** `Application startup` with hostname/IP
- **Validation Errors:** `Validation failed for field 'name'`

### Usage

```python
from src.logging_config import get_logger

logger = get_logger(__name__)

# Structured logging with key-value pairs
logger.info("Object created", object_name="Pizza", object_id=123, user="anonymous")
logger.warning("Validation failed", field="name", error="cannot be empty")
```

**Security:** Sensitive fields (passwords, tokens) automatically redacted.

## Deployment

### Docker

```bash
# Build image
docker build -t savt .

# Run container
docker run -p 8000:8000 --env-file .env savt

# Docker Compose (includes PostgreSQL)
docker compose up --build
```

### Production Considerations

- Use PostgreSQL for production (not SQLite)
- Configure `DATABASE_URL` environment variable
- Set `LOG_LEVEL=INFO` for production logging
- Enable HTTPS via reverse proxy (nginx, Caddy)
- Review security settings in `.env`

## API Documentation

Interactive API documentation available at:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

All endpoints use `/api/v1/` prefix for versioning.

## Code Quality Standards

- **Python 3.13+** with modern type hints (`list[str]`, `int | None`)
- **88-character line limit** (Black/Ruff default)
- **4 spaces** for Python (PEP 8)
- **2 spaces** for HTML/CSS/JS (web standard)
- **All files end with newline** (enforced by QA)
- **Pinned dependencies** (`==` in `pyproject.toml`)

### QA Tools

- **ruff** - Ultra-fast linting + formatting
- **mypy** - Static type checking
- **djlint** - HTML/Jinja2 template formatting
- **pytest** - Testing framework with parallel execution
- **Custom QA tool** - Unified interface (`uv run qa check`)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes following code quality standards
4. Run QA: `uv run qa check`
5. Run tests: `uv run pytest`
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

[Add your license here]

## Acknowledgments

Built with modern Python tooling:
- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [FastAPI](https://fastapi.tiangolo.com/) - High-performance web framework
- [HTMX](https://htmx.org/) - HTML-over-the-wire interactivity
- [SQLModel](https://sqlmodel.tiangolo.com/) - Type-safe SQL ORM

---

**For detailed development guidance**, see [CLAUDE.md](./CLAUDE.md)
