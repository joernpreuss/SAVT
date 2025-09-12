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

## Development Details

For comprehensive development guidance, configuration details, and project history, see [CLAUDE.md](./CLAUDE.md).
