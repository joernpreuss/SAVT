# SAVT Development Guide

This file contains information for AI assistants and developers working on the SAVT project.

## Quick Commands

### Development

- **Start server**: `uv run uvicorn src.main:app --reload --host 0.0.0.0`
- **Run tests**: `uv run pytest`
- **Lint**: `uv tool run ruff check src/ tests/`
- **Format**: `uv tool run ruff format src/ tests/`
- **Typecheck**: `uv tool run mypy src/`
- **All checks**: `./scripts/check.sh` (installs tools: `uv tool install ruff mypy`)

### Deployment
- **Docker build**: `docker build -t savt .`
- **Docker run**: `docker run -p 8000:8000 savt`
- **Docker Compose**: `docker-compose up --build`

### Project Structure

```text
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
    ├── objects_list.html
    └── standalone_properties.html

tests/                       # Test files
```

## Architecture Notes

### Tech Stack

- **FastAPI** - Modern Python web framework
- **SQLModel** - Type-safe database models
- **Jinja2** - Server-side templating
- **HTMX** - Dynamic frontend without JavaScript
- **uv** - Fast Python package management

### Key Design Decisions

1. **Pure Python**: Avoiding JS/TS complexity while maintaining modern UX
2. **HTMX Integration**: Progressive enhancement with fallback support
3. **Server-side rendering**: All logic stays in Python
4. **SQLite**: Simple file-based database for development

### Database Models

- `SVObject`: Represents items for group decisions (e.g., pizzas)
- `SVProperty`: Represents options/properties (e.g., toppings)
- Properties can be vetoed by users (stored as JSON array)

### HTMX Implementation

- Veto/unveto actions update without page reload
- Forms submit via AJAX with immediate feedback
- Fragment templates for partial page updates
- Graceful degradation with standard href fallbacks

## Common Tasks

### Adding New Features

1. Update models in `models.py` if database changes needed
2. Add business logic to `service.py`
3. Create routes in `routes.py` (HTML) or `api_routes.py` (JSON)
4. Update templates for UI changes
5. Add HTMX fragment templates for dynamic updates

### Debugging

- Check server logs for errors
- Use FastAPI's automatic `/docs` endpoint for API testing
- HTMX requests include `HX-Request` header for detection

## CI/CD Pipeline

### GitHub Actions
- **CI Pipeline** (`.github/workflows/ci.yml`):
  - Runs on push/PR to main branch
  - Linting, formatting, type checking
  - Test execution and server startup verification
  - Matrix testing across Python versions

- **Deployment Pipeline** (`.github/workflows/deploy.yml`):
  - Triggers on main branch pushes
  - Builds and deploys application
  - Health checks and notifications

### Docker Support
- **Dockerfile**: Multi-stage build with uv and non-root user
- **docker-compose.yml**: Local development setup
- **Health checks**: Built-in container health monitoring

## Development History

- Started as pizza ordering proof of concept
- Migrated from requirements.txt to uv/pyproject.toml
- Added HTMX for dynamic interactions
- Removed problematic debug toolbar middleware
- Updated Pydantic config from deprecated class-based to ConfigDict
- Added comprehensive CI/CD pipeline with Docker support
