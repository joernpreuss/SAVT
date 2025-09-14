# SAVT Development Documentation

Extended development guidance for the SAVT project.

> **Note**: This file contains detailed documentation that was moved from CLAUDE.md to keep the AI assistant guidance concise and context-window friendly. For AI-specific essentials, see [CLAUDE.md](../CLAUDE.md).

## Configuration

- **Environment file**: Copy `.env.example` to `.env` and customize
- **Pydantic Settings**: Type-safe config with validation and .env support
- **Key variables**: `DEBUG`, `DATABASE_URL`, `HOST`, `PORT`, `SECRET_KEY`
- **Validation**: Built-in validation (e.g., port range 1-65535, secret key min length)

## Development Tooling

- **Editor Config**: `.editorconfig` ensures consistent formatting across editors
- **Pre-commit Hooks**: `.pre-commit-config.yaml` runs linting/formatting before commits
- **VS Code Settings**: `.vscode/settings.json` configures automatic formatting and linting
- **Setup pre-commit**: `uv add --dev pre-commit && pre-commit install` (optional but recommended)
- **HTML/Jinja2 Formatting**: djLint integrated into QA tool with `.djlintrc` config
  - Ignores J018 (url_for pattern) - FastAPI doesn't use Flask's url_for
  - Ignores J004 (static url_for pattern) - FastAPI serves static files differently
  - Enforces HTML best practices (lang attribute, meta tags, lowercase form methods)

## Detailed Architecture

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

## Common Development Tasks

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
- Fixed test suite: resolved HTMX fragment issues, template deprecation warnings, and empty name validation
- Added development tooling: .editorconfig, pre-commit hooks, VS Code settings for consistent formatting
