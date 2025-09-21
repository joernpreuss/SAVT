# SAVT Development Guide

AI assistant development guidance for the SAVT project. See [README.md](./README.md) for basic commands and setup.

## Key Architecture

- **Layered Architecture** - Domain-driven design with clean separation of concerns
  - Domain: `src/domain/` - Pure business entities, constants, exceptions (no dependencies)
  - Application: `src/application/` - Business logic and services
  - Infrastructure: `src/infrastructure/database/` - Database persistence, SQLModel mapping
  - Presentation: `src/presentation/` - API and web routes
- **FastAPI + SQLModel** - Python web framework with type-safe database
- **Jinja2 + HTMX** - Server-side templates with dynamic interactions (no JS)
- **Feature IDs**: Use `feature.id` for unique identification, not `feature.name` (allows duplicate names)
- **Veto system**: Users can veto/unveto features independently using feature IDs
- **API versioning**: All API endpoints use `/api/v1/` prefix for future compatibility
- **HTTP status codes**: 201 for creation (POST new resources), 200 for actions/updates

## Development Standards

- Python: 4 spaces (PEP 8), modern type hints (`list[str]`, `int | None` not `List[str]`, `Optional[int]`)
- HTML/CSS/JS: 2 spaces (web standard, defined in `.editorconfig`)
- File endings: All files must end with newline (enforced by `.editorconfig` and QA tool)
- Package management: Use `uv add` instead of `pip install` (faster, better dependency resolution)
- QA tool: `./qa check` runs linting, formatting, type checking, template linting, tests
- **When user says "qa"**: Run `./qa check` and select SQLite tests with option 1 (single-threaded)
- **QA Interactive**: Rerun individual checks from test menu, ESC to quit, shows results before fixes
- djLint: Integrated HTML/Jinja2 formatter, ignores J018/J004 (FastAPI-specific)
- Ruff format: Run `ruff format` after every change

## Development Protocol

**CRITICAL: After EVERY change:**

1. **ALWAYS** run `./qa check` immediately
2. **ALWAYS** run tests to verify functionality
3. Fix ALL issues until both are 100% green
4. Check for redundancy - Always verify no unused files or duplicate code exists:
   - Unused files - Search for imports to verify files are still referenced
   - Duplicate code - Look for similar functions across modules (validation, helpers)
   - Dead code - Delete unused implementations and imports
   - Validate - Run `./qa check` after cleanup to ensure no broken imports
5. Only then proceed with next changes

**REMEMBER**: ALWAYS QA AND TEST. Both are mandatory after any code change.

**Never work with broken QA or failing tests.** They are not gates at the end - they are compasses throughout development.

## Git Workflow

- NEVER execute `git add` - Only the user stages files
- NEVER execute `git commit` - Only the user commits code
- NEVER execute `git push` - Only the user pushes changes
- Use "cm" keyword for commit messages - Type "commit" to get a suggested commit message for current changes
- No automatic git operations - All git commands must be explicitly requested by user

## Important Files

- `src/application/item_service.py` - Item CRUD operations
- `src/application/feature_service.py` - Feature CRUD and veto operations
- `src/application/item_operations_service.py` - Complex operations (merge/split/move)
- `src/presentation/routes.py` - HTML routes
- `src/presentation/api_routes.py` - JSON API with comprehensive OpenAPI documentation
- `src/domain/entities.py` - Pure domain entities (dataclasses)
- `src/infrastructure/database/models.py` - SQLModel persistence models
- `templates/macros.html` - Jinja2 macros for veto/unveto functionality
- `.djlintrc` - HTML formatter config
