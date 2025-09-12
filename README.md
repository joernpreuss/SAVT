# SAVT

Pure Python Suggestion And Veto Tool

## Overview

SAVT is a collaborative decision-making tool originally designed as a proof of concept for ordering pizza together. The system allows users to:

- Create **objects** (like pizzas or any item requiring group decisions)
- Suggest **properties** for those objects (like toppings: salami, mushrooms, extra cheese)
- **Veto** properties they don't want, enabling democratic consensus-building

While initially built for pizza ordering, the flexible object-property model makes it suitable for any group decision-making scenario where suggestions and vetoes help reach consensus.

## Technical Approach

SAVT is built with **pure Python** to avoid the complexity of JavaScript/TypeScript frameworks. The interactive features are powered by:

- **FastAPI** - Modern Python web framework for the backend API
- **Jinja2** - Server-side HTML templating
- **HTMX** - Adds dynamic interactivity without writing JavaScript
- **SQLModel** - Python-first database interactions

This approach provides a responsive, interactive web experience while keeping all logic in Python. HTMX enables instant updates for veto/unveto actions and smooth form submissions without page reloads.

## Development

### Prerequisites

If you don't have `uv` installed:
```bash
pip install uv
```

### Package Management

**Always use `uv` instead of `pip` for this project:**
- Install dependencies: `uv add package-name`
- Install dev dependencies: `uv add --dev package-name`  
- Run commands: `uv run command`
- Sync environment: `uv sync`

Python version is pinned to 3.12 via `.python-version` to ensure consistent behavior.

### Quick Commands

- **Start server**: `uv run uvicorn src.main:app --reload --host 0.0.0.0`
- **Run tests**: `uv run pytest`
- **Lint**: `uv tool run ruff check src/ tests/`
- **Format**: `uv tool run ruff format src/ tests/`
- **Typecheck**: `uv tool run mypy src/`
- **All checks**: `./scripts/check.sh`
- **All checks + auto-fix**: `./scripts/check.sh --fix`

**Configuration:** Line length set to 88 characters (Black/PEP 8 standard, configurable in `pyproject.toml`)

**Modern Python Typing:** This project uses Python 3.12+ modern typing syntax:
- Use `dict[str, int]` instead of `Dict[str, int]`
- Use `list[str]` instead of `List[str]`
- Use `tuple[int, ...]` instead of `Tuple[int, ...]`
- No need to `from typing import Dict, List, Tuple` etc.

**Install tools:** `uv tool install ruff mypy`

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

tests/                       # Test files
```

### Deployment

- **Docker build**: `docker build -t savt .`
- **Docker run**: `docker run -p 8000:8000 --env-file .env savt`
- **Docker Compose**: `docker-compose up --build`

## Logging System

SAVT includes a comprehensive structured logging system with different loggers for different concerns:

### Log Types

- **API Requests**: `GET /api/endpoint - 200 (15.2ms)` 
- **User Actions**: `User action: veto_property by anonymous`
- **Database Operations**: `Database create on SVObject succeeded`
- **System Events**: `Application startup` with hostname/IP
- **Validation Errors**: `Validation failed for field 'name': too short`

### Configuration

- **Development**: Rich console output with syntax highlighting
- **Production**: File logging to `logs/savt.log` + console
- **Security**: Sensitive fields (passwords, tokens) automatically redacted as `[REDACTED]`
- **Performance**: Third-party loggers (SQLAlchemy, Uvicorn) are filtered to reduce noise

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
