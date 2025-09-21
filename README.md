# SAVT

Pure Python Suggestion And Veto Tool

> **Experimental AI-Assisted Development**: This project serves as an experiment in AI-assisted coding, exploring deliberate architectural choices like pure Python (no JS/TS), server-side HTML but with HTMX for dynamic interactions, modern tooling (uv, type hints), and comprehensive requirement tracing. Many decisions were made intentionally to test specific approaches and patterns.

Built with **uv** - the modern, fast Python package manager that's significantly faster than pip with better dependency resolution and built-in virtual environment management. uv replaces pip, pip-tools, virtualenv, and pyenv in one tool.

## Overview

SAVT is a collaborative decision-making platform designed for any group decision - from simple social choices to complex business workflows. The system enables democratic consensus-building through a suggestion and veto model:

- **Create decision items** (projects, events, purchases, policies, etc.)
- **Democratic suggestions** - Anyone can propose options or features
- **Veto-based consensus** - Participants can block options they strongly oppose
- **Flexible data model** - Works for any type of group decision

**Use Cases:**
- **Business decisions:** vendor selection, budget allocation, policy changes
- **Development workflows:** code reviews, deployments, architecture choices
- **Team coordination:** meeting scheduling, project priorities, resource allocation
- **Social planning:** restaurant choices, event planning, group activities

The pizza ordering example demonstrates the concept, but SAVT's flexible architecture supports any collaborative decision-making scenario.

## Technical Approach

SAVT is built with pure Python to avoid JavaScript/TypeScript complexity, using server-side HTML generation with HTMX for dynamic interactions. This means all HTML is generated on the server using Jinja2 templates, while HTMX enables partial page updates and interactive features without writing JavaScript.

**Key Architecture:**

- Feature IDs: Uses `feature.id` for unique identification (allows duplicate feature names)
- Veto System: Users can independently veto/unveto features using unique IDs
- No-JavaScript Architecture: HTMX provides SPA-like interactions (partial updates, form submissions) while keeping all logic in Python

## Development

### Prerequisites

**System Requirements:**

- Python 3.12+ (pinned via `.python-version`)
- uv - Install with: `pip install uv`

**Key Technologies:**

- FastAPI + SQLModel - Modern Python web framework with type-safe database
- Jinja2 + HTMX - Server-side templating with dynamic interactions
- pytest + structlog - Testing and structured logging
- PostgreSQL + SQLite - Configurable database backend (SQLite default, PostgreSQL for production)

Dependencies are managed via `pyproject.toml` with exact version pinning for reproducibility.

### Development Setup

```bash
# Install dependencies and sync environment
uv sync

# Install development tools
uv tool install ruff mypy
```

### Development Commands

- Start server: `uv run uvicorn src.main:app --reload --host 0.0.0.0`
- Run tests: `uv run pytest`
- Test with docstrings: `uv run pytest --show-docstrings` (displays test requirements during execution)
- Requirements coverage: `uv run pytest -v` (shows FR/BR coverage in verbose mode)
- Requirements only: `uv run pytest --requirements-report -q` (coverage without running tests)
- All checks: `./qa check` (interactive menu with rerun options)
- Auto-fix all: `./qa check --fix-all`
- Individual commands: `./qa format`, `./qa lint`, `./qa typecheck`, `./qa newlines`
- Raw tools: `uv tool run ruff check src/`, `uv tool run mypy src/`

**QA Tool Features:**
- **Interactive rerun options**: After checks complete, rerun individual tools (formatter, linter, etc.) from test selection menu
- **Template formatting**: Unified code + template formatting with `./qa format` (ruff + djlint)
- **ESC key support**: Press ESC to quit from any menu quickly
- **Smart workflow**: Shows results first, then asks for fixes (no more blind fix prompts)

### Testing

**Fast Tests (Default - In-Memory SQLite):**
```bash
# Run all tests with in-memory SQLite (fast)
uv run pytest

# Run tests in parallel
uv run pytest -n10

# Run all tests simultaneously (proves concurrency design)
uv run pytest -n72
```

**Integration Tests (PostgreSQL):**
```bash
# Set up PostgreSQL test database first
createdb savt_test  # or use your PostgreSQL setup

# Run tests against PostgreSQL
TEST_DATABASE=postgresql DATABASE_URL=postgresql://user:password@localhost:5432/savt uv run pytest

# Run PostgreSQL tests in parallel (tests real concurrency)
TEST_DATABASE=postgresql DATABASE_URL=postgresql://user:password@localhost:5432/savt uv run pytest -n10
```

**Test Types Explained:**

- **Unit Tests (SQLite)**: Fast, isolated, CI-friendly, perfect for development
- **Integration Tests (PostgreSQL)**: Realistic, tests actual concurrency and connection pooling

**Environment Variables:**
- `TEST_DATABASE=postgresql` - Use PostgreSQL for tests instead of SQLite
- `DATABASE_URL` - PostgreSQL connection string (tests use `*_test` suffix automatically)

**Code Style:** 88-character lines, Python 3.12+ modern typing (`dict[str, int]` not `Dict[str, int]`)

### Configurable Terminology

The app terminology is fully configurable for different use cases. **Plural forms are automatically generated** by adding "s" to singular forms, so you usually only need to set the singular terms:

**Pizza Ordering Example:**

```bash
cp .env.pizza .env  # Use pizza/toppings terminology
```

**Simple Configuration (Auto-Pluralization):**

```bash
# In your .env file:
APP_NAME="My Voting Tool"
OBJECT_NAME_SINGULAR="item"        # Automatically becomes "items"
PROPERTY_NAME_SINGULAR="feature"   # Automatically becomes "features"
```

**Override for Irregular Plurals:**

```bash
# When the simple "add s" rule doesn't work:
OBJECT_NAME_SINGULAR="category"
OBJECT_NAME_PLURAL="categories"    # Override automatic "categorys"
PROPERTY_NAME_SINGULAR="child"
PROPERTY_NAME_PLURAL="children"    # Override automatic "childs"
```

**Example Configurations:**

- **Pizza ordering**: `pizza` → `pizzas`, `topping` → `toppings`
- **Feature voting**: `feature` → `features`, `aspect` → `aspects`
- **Event planning**: `event` → `events`, `option` → `options`
- **Product design**: `product` → `products`, `component` → `components`
- **Library system**: `book` → `books`, `category` → `categories` (override needed)

## Requirements Traceability System

SAVT includes a **novel requirements traceability system** that automatically extracts functional requirements (FR) and business rules (BR) from test docstrings and generates coverage reports. This bridges the gap between formal requirements management and agile development.

### How It Works

Tests reference requirements in their docstrings using a simple pattern:

```python
def test_create_property_conflict(session: Session, timestamp_str: str):
    """Test property name uniqueness enforcement.

    Covers:
    - FR-2.3: Property names must be unique within their scope
    - FR-2.4: System prevents duplicate property creation (returns 409 error)
    """
    # Test implementation...
```

### Coverage Features

- Automatic extraction from docstrings using regex patterns (`FR-X.Y`, `BR-X.Y`)
- Real-time reporting during test execution
- Coverage analysis showing which requirements are tested
- Git-friendly - no external databases, all embedded in code
- Developer-friendly - integrates seamlessly with existing pytest workflows

### Usage Examples

```bash
# Show test docstrings with requirements during execution
uv run pytest --show-docstrings

# Generate requirements coverage report
uv run pytest -v

# Coverage analysis without running tests
uv run pytest --requirements-report -q

# Requirements-only mode (skip test execution)
uv run pytest --requirements-only
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

This system makes requirements traceability practical for everyday development, unlike heavy enterprise tools or manual spreadsheets that teams typically abandon.

### Project Structure

```
src/
├── main.py          # FastAPI app entry point
├── routes.py        # Web routes (HTML responses)
├── api_routes.py    # API routes (JSON responses)
├── models.py        # SQLModel database models
├── service.py       # Business logic
├── database.py      # Database connection
└── utils.py         # Utilities

templates/
├── properties.html           # Main page template
└── fragments/               # HTMX partial templates

tests/                       # Test files with requirements traceability
├── pytest_requirements.py  # Custom pytest plugin for FR/BR extraction
└── test_*.py               # Test files with FR/BR references in docstrings
```

### Database Configuration

SAVT supports both SQLite and PostgreSQL databases:

**SQLite (Default)**
```bash
# Uses SQLite by default (no setup required)
uv run uvicorn src.main:app --reload
```

**PostgreSQL (Production Ready)**
```bash
# Quick setup with Docker
./scripts/postgres.sh setup

# Or manually
docker compose up -d postgres
cp .env.postgres .env
uv run uvicorn src.main:app --reload
```

**PostgreSQL Management**
```bash
./scripts/postgres.sh start      # Start PostgreSQL container
./scripts/postgres.sh status     # Check status and health
./scripts/postgres.sh shell      # Connect to database shell
./scripts/postgres.sh logs       # View container logs
./scripts/postgres.sh reset      # Reset database (DELETE ALL DATA)
```

See [POSTGRESQL.md](./POSTGRESQL.md) for complete setup guide and troubleshooting.

### Deployment

- Docker build: `docker build -t savt .`
- Docker run: `docker run -p 8000:8000 --env-file .env savt`
- Docker Compose: `docker compose up --build`

## Logging System

SAVT includes a comprehensive structured logging system with different loggers for different concerns:

### Log Types

- API Requests: `GET /api/endpoint - 200 (15.2ms)`
- User Actions: `User action: veto_property by anonymous`
- Database Operations: `Database create on SVObject succeeded`
- System Events: `Application startup` with hostname/IP
- Validation Errors: `Validation failed for field 'name': too short`

### Configuration

- Development: Rich console output with syntax highlighting
- Production: File logging to `logs/savt.log` + console
- Security: Sensitive fields (passwords, tokens) automatically redacted as `[REDACTED]`
- Performance: Third-party loggers (SQLAlchemy, Uvicorn) are filtered to reduce noise

### Usage in Code

```python
from src.logging_config import get_logger
from src.logging_utils import log_user_action, log_database_operation

logger = get_logger(__name__)

# Structured logging with key-value pairs (NEW with structlog)
logger.info("Object created", object_name="Pizza", object_id=123, user="anonymous")
logger.warning("Validation failed", field="name", value="", error="cannot be empty")
logger.debug("Processing request", method="POST", path="/veto", user="anonymous")

# Legacy specialized loggers (still available)
log_user_action("create_property", user="anonymous", object_name="Pizza")
log_database_operation("create", "SVObject", success=True, object_id=123)
```

**Development output:**

```
2024-01-01T10:00:00 [info     ] Object created                 object_name=Pizza object_id=123 user=anonymous
```

**Production output (JSON):**

```json
{"timestamp": "2024-01-01T10:00:00.123Z", "level": "info", "event": "Object created", "object_name": "Pizza", "object_id": 123, "user": "anonymous", "logger": "src.routes"}
```

## Development Details

For comprehensive development guidance, configuration details, and project history, see [CLAUDE.md](./CLAUDE.md).
