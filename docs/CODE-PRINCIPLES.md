# SAVT Code Principles

**Clean/Agentic Code Principles** - Extracted from codebase, documentation, and git history

**Last Updated:** 2025-11-16

---

## Overview

This document captures the code principles and design philosophy that guide SAVT development. These principles emerged organically through practical development and are evidenced throughout the codebase, documentation, and git history.

**Philosophy**: Principles should be discoverable by reading the code, not hidden in external documents. This document serves as a reference guide, but the code itself is the authoritative source.

---

## Table of Contents

1. [Architectural Principles](#architectural-principles)
2. [Code Quality Principles](#code-quality-principles)
3. [Development Workflow Principles](#development-workflow-principles)
4. [Design Philosophy Principles](#design-philosophy-principles)
5. [Tooling Principles](#tooling-principles)
6. [API Design Principles](#api-design-principles)
7. [Documentation Principles](#documentation-principles)
8. [Git Workflow Principles](#git-workflow-principles)
9. [Testing Principles](#testing-principles)
10. [Observability Principles](#observability-principles)

---

## Architectural Principles

### 1. Clean Architecture with Domain-Driven Design

**Principle**: Organize code in strict layers with unidirectional dependencies flowing inward toward the domain.

**Layers** (from innermost to outermost):
1. **Domain** (`src/domain/`) - Pure business logic, zero dependencies
2. **Application** (`src/application/`) - Business logic orchestration
3. **Infrastructure** (`src/infrastructure/`) - Database, external services
4. **Presentation** (`src/presentation/`) - API routes, web UI

**Evidence**:
- `src/domain/entities.py:1-10` - Pure dataclasses with only domain imports
- `src/application/feature_service.py:7-12` - Application imports domain, not vice versa
- Git commit `730ebbb` - Refactored to maintain layer separation during soft delete implementation

**Benefits**:
- Testability - Domain logic testable without database
- Maintainability - Clear boundaries make code location obvious
- Flexibility - Easy to swap infrastructure (SQLite ↔ PostgreSQL)

### 2. Domain Entity Purity

**Principle**: Domain entities are pure dataclasses with zero external dependencies - no database, no logging, no framework code.

**Rules**:
- Use `@dataclass` for entities (not SQLModel)
- Validation in `__post_init__` using pure functions
- Only import from `domain.constants` and `domain.exceptions`
- Business rules live in entity methods

**Evidence**:
```python
# src/domain/entities.py:41-75
@dataclass
class Item:
    """Core business entity representing an item (e.g., pizza)."""
    id: int | None
    name: str
    kind: str | None = None
    created_by: str | None = None
    deleted_at: datetime | None = None

    def __post_init__(self):
        """Validate item data after initialization."""
        self.validate()

    def validate(self) -> None:
        """Validate item business rules."""
        validate_entity_name(self.name, "item")
        # ... pure validation logic
```

**Anti-pattern**:
```python
# NEVER in domain layer
from sqlmodel import SQLModel
from structlog import get_logger
```

### 3. Service Functions Over Classes

**Principle**: Use module-level functions for services instead of classes. No singletons, no class state.

**Evidence**:
- `src/application/feature_service.py` - All functions at module level
- `src/application/item_service.py` - CRUD as pure functions with session injection

**Rationale**:
- Simpler - No `self` parameter, no `__init__`
- Explicit - Session always passed as parameter
- Testable - Easy to mock dependencies
- Pythonic - Aligns with functional programming style

### 4. Bridge Pattern for Persistence

**Principle**: Separate domain entities from database models using explicit conversion methods.

**Implementation**:
```python
# src/infrastructure/database/models.py
class Feature(SQLModel, table=True):
    # ... database fields

    def to_domain(self) -> DomainFeature:
        """Convert database model to domain entity."""
        # Explicit conversion

    @staticmethod
    def from_domain(feature: DomainFeature) -> "Feature":
        """Convert domain entity to database model."""
        # Explicit conversion
```

**Evidence**: Git commit `730ebbb` - Maintained separation during soft delete refactor

**Benefits**:
- Domain remains pure (no ORM leakage)
- Easy to change database technology
- Clear conversion points for debugging

### 5. Dependency Injection via Parameters

**Principle**: Explicitly pass dependencies as function parameters. No global state, no service locators.

**Evidence**:
```python
# src/application/feature_service.py:21-27
def get_features(session: Session) -> Sequence[Feature]:
    """Get all features - session injected explicitly."""
    statement: Final = select(Feature).where(...)
    # ...
```

**Testing Pattern**:
```python
# tests/conftest.py - Override FastAPI dependencies
app.dependency_overrides[get_db] = lambda: test_session
```

---

## Code Quality Principles

### 6. Modern Python Type Hints

**Principle**: Use Python 3.13+ modern type hints everywhere. Types are documentation and safety.

**Rules**:
- Use `list[str]` not `List[str]` (built-in generics)
- Use `int | None` not `Optional[int]` (PEP 604 union syntax)
- Use `Final` for immutable values
- Type all function signatures

**Evidence**:
- `pyproject.toml:10` - `requires-python = "~=3.13.0"`
- `CLAUDE.md:29` - "modern type hints (`list[str]`, `int | None`)"
- `src/application/feature_service.py:22-26` - Comprehensive type annotations

**Tooling**:
- `mypy` for static type checking
- Ruff for style enforcement
- Pylance/Pyright for IDE support

### 7. Pinned Dependencies

**Principle**: Pin all dependencies with exact versions (`==`). No `>=` or `^` for production stability.

**Evidence**:
```toml
# pyproject.toml:11-27
dependencies = [
    "fastapi==0.116.2",
    "jinja2==3.1.6",
    "python-multipart==0.0.20",
    # ... all pinned with ==
]
```

**Rationale**:
- Reproducible builds across environments
- Predictable CI/CD behavior
- Easy to audit security vulnerabilities
- Explicit upgrade decisions

### 8. Validation in Three Layers

**Principle**: Validate data at three distinct layers, each with different responsibilities.

**Layers**:

1. **Domain Layer** - Pure business rules
   ```python
   # src/domain/entities.py:10-39
   def validate_entity_name(name: str, entity_type: str = "entity") -> None:
       """Pure validation - no logging, no DB"""
       if not name or not name.strip():
           raise ValidationError(f"{entity_type.title()} name cannot be empty")
   ```

2. **Application Layer** - Same rules + logging
   ```python
   # src/application/validation.py
   def validate_entity_name_with_logging(name: str, entity_type: str) -> None:
       """Validation with structured logging"""
       try:
           validate_entity_name(name, entity_type)
       except ValidationError:
           logger.warning("Validation failed", field="name", ...)
           raise
   ```

3. **Presentation Layer** - User-friendly error messages
   ```python
   # src/presentation/error_handlers.py
   def handle_validation_error(error: ValidationError):
       """Convert to RFC 7807 Problem Details or HTML error page"""
   ```

**Evidence**: Git commit `1f80f52` - Implemented three-tier error handling

### 9. QA as Compass, Not Gate

**Principle**: QA tools (linting, formatting, type checking, tests) are continuous feedback, not end-of-project gates.

**Mandates**:
- Run QA after **every** change
- Fix all issues before proceeding
- Never work with broken QA or failing tests
- QA failures block further development

**Evidence**:
- `CLAUDE.md:55-69` - "After EVERY change: 1. Run QA, 2. Run tests, 3. Fix ALL issues"
- `CLAUDE.md:67-69` - "Never work with broken QA or failing tests. They are not gates at the end - they are compasses throughout development."

**Tooling**:
```bash
uv run qa check              # Interactive QA with rerun options
uv run qa format             # Format code + templates
uv run qa lint               # Lint code
uv run qa typecheck          # Type checking
pytest                       # Run tests
```

### 10. File Endings Must Include Newline

**Principle**: All files must end with a newline character. No exceptions.

**Evidence**:
- `.editorconfig` - `insert_final_newline = true`
- `tools/check_newlines.py` - Automated verification
- `CLAUDE.md:31` - "File endings: All files must end with newline"

**Rationale**:
- POSIX standard compliance
- Better git diffs
- Prevents concatenation issues
- Unix tool compatibility

---

## Development Workflow Principles

### 11. UV for All Python Operations

**Principle**: Use `uv` exclusively for package management and Python execution. Never use `pip` or bare `python`.

**Commands**:
```bash
uv sync                      # Install dependencies
uv add package==1.0.0        # Add dependency
uv run pytest                # Run commands in venv
uv run uvicorn src.main:app  # Start server
```

**Evidence**:
- `CLAUDE.md:26-28` - "ALWAYS use `uv` to run python commands"
- `README.md:70` - "uv sync" for installation
- Git commit `d815596` - Configured nox to use uv backend

**Benefits**:
- 10-100x faster than pip
- Better dependency resolution
- Unified tool (replaces pip, virtualenv, pyenv)
- Lockfile generation

### 12. Reduce Redundancy (rr)

**Principle**: Actively hunt and eliminate code redundancy. Shared logic belongs in shared modules.

**Evidence**:
- `CLAUDE.md:49` - "When user says 'rr': This means 'reduce redundancy'"
- Git commit `a76c5ac` - "Reduce redundancy and optimize nox integration"
- Git commit `6b57989` - "Eliminate redundancy in qa.py"

**Redundancy Types**:
- **Duplicate code** - Similar functions across modules
- **Unused files** - No imports referencing them
- **Dead code** - Unreachable or obsolete implementations
- **Copy-paste logic** - Consolidate into shared utilities

**Example**:
```python
# BEFORE: Duplicate veto logic in multiple routes
# routes.py line 150
if user not in feature.vetoed_by:
    feature.vetoed_by.append(user)

# routes.py line 320
if user not in feature.vetoed_by:
    feature.vetoed_by.append(user)

# AFTER: Shared utility
# utils.py
def apply_veto_to_feature(feature: Feature, user: str) -> None:
    """Apply veto to feature (idempotent)."""
    if user not in feature.vetoed_by:
        feature.vetoed_by.append(user)
```

### 13. ISO 8601 Date Formatting

**Principle**: Always use ISO 8601 format (YYYY-MM-DD) for all dates in documentation and logs.

**Evidence**:
- `CLAUDE.md:50` - "Date formatting: Always use ISO 8601 format (YYYY-MM-DD)"
- This document header - `2025-11-16`

**Rationale**:
- Unambiguous (no US vs EU confusion)
- Sortable lexicographically
- International standard
- Machine-readable

---

## Design Philosophy Principles

### 14. Simplicity Over Complexity

**Principle**: Choose the simplest solution that works. Avoid premature abstraction.

**Evidence**:
- Trust-based user system (no OAuth, no JWT)
- Cookie-based username (no session database)
- SQLite for development (no PostgreSQL setup required)
- Server-side rendering (no JavaScript build pipeline)

**Git Commit Evidence**:
- Commit `aeaa57c` - "Lightweight user system... Trust-based user system for co-located teams"
- Removed separate undo tables in favor of soft deletes (commit `730ebbb`)

### 15. Transparency by Default

**Principle**: Make system behavior visible. No hidden magic.

**Evidence**:
- Veto transparency - Show who vetoed, not just count
  - Before: `(2 vetoes)`
  - After: `(vetoed by: Alice, Bob)`
- Structured logging with context
- OpenAPI documentation auto-generated
- Requirements traceability in test docstrings

**Code Example**:
```jinja2
{# templates/macros.html - Transparent veto display #}
{% if feature.vetoed_by|length > 0 %}
  <span class="veto-users">
    (vetoed by: {{ feature.vetoed_by|join(', ') }})
  </span>
{% endif %}
```

### 16. Trust-Based Collaboration

**Principle**: Design for cooperative teams, not adversarial environments. Optimize for usability over security when appropriate.

**Evidence**:
- No authentication (trust-based usernames)
- No permission system (all users equal)
- Easy username switching (feature, not bug)
- Public veto information (transparency over privacy)

**Documentation**:
- `docs/USER-SYSTEM-DESIGN.MD:9-17` - "Trust-Based Collaboration: Like a board game where players announce their identity"
- Acceptable use cases: Small co-located teams (2-10 people)
- Unacceptable: Public-facing applications, competitive voting

### 17. Progressive Enhancement

**Principle**: Build features that work without JavaScript, then enhance with HTMX for better UX.

**Implementation**:
- All forms work with traditional POST
- HTMX adds fragment updates (no full page reload)
- Graceful degradation if JavaScript disabled

**Evidence**:
```html
<!-- templates/macros.html - Works with/without HTMX -->
<form method="post" action="/veto/feature/{{ feature.name }}"
      hx-post="/veto/feature/{{ feature.name }}"
      hx-target="#properties-list"
      hx-swap="outerHTML">
  <!-- Falls back to standard form submission -->
</form>
```

---

## Tooling Principles

### 18. Modern Python Tooling

**Principle**: Use modern, fast, type-safe tooling exclusively.

**Tool Stack**:
- **uv** - Package management (replaces pip, virtualenv, pyenv)
- **Ruff** - Linting + formatting (replaces Black, isort, flake8)
- **mypy** - Static type checking
- **djLint** - HTML/Jinja2 formatting
- **pytest** - Testing framework with parallel execution
- **structlog** - Structured logging

**Evidence**:
- Git commit `39f2ee6` - "Modernize tooling and improve code quality"
- `pyproject.toml:53-75` - Ruff configuration replacing multiple tools

### 19. Unified QA Interface

**Principle**: Provide a single, interactive QA tool that runs all quality checks with smart workflows.

**Features**:
- Interactive menu with rerun options
- Shows results first, then offers fixes
- ESC key support for quick quit
- Individual commands for targeted checks

**Evidence**:
- `README.md:102-110` - QA tool documentation
- Git commit `be8d7de` - "Add nox automation and fix QA tool newlines display"
- `CLAUDE.md:47` - "When user says 'qa': Run the individual QA commands"

**Usage**:
```bash
uv run qa check              # Interactive QA
uv run qa check --fix-all    # Auto-fix all issues
uv run qa format             # Format code + templates
uv run qa lint               # Lint only
uv run qa typecheck          # Type check only
```

### 20. Fast Feedback Loops

**Principle**: Optimize for developer productivity with instant feedback.

**Implementations**:
- Parallel test execution (`pytest -n10`)
- Hot reload development server (`--reload`)
- Pre-commit hooks (optional but recommended)
- Instant QA checks via IDE integration

**Evidence**:
- `pytest.ini` - xdist configuration for parallel tests
- `.vscode/settings.json` - Format on save
- `README.md:117` - `pytest -n10` for parallel execution

---

## API Design Principles

### 21. API Versioning from Day One

**Principle**: All API endpoints include version prefix (`/api/v1/`). Plan for future breaking changes.

**Evidence**:
- All API routes: `/api/v1/items`, `/api/v1/features`, etc.
- `CLAUDE.md:18` - "API versioning: All API endpoints use `/api/v1/` prefix"
- `README.md:52` - "API versioning (`/api/v1/`) for forward compatibility"

**Rationale**:
- Easy to introduce `/api/v2/` later
- Clients can opt-in to new versions
- Gradual migration path
- No breaking changes for existing clients

### 22. Dual Response Formats (HTML + JSON)

**Principle**: Support both HTML (for web UI) and JSON (for API clients) from the same application.

**Implementation**:
- HTML routes: `/items`, `/features` (for browser)
- API routes: `/api/v1/items`, `/api/v1/features` (for clients)
- Error handlers detect request type and format accordingly

**Evidence**:
```python
# src/presentation/error_handlers.py - Dual format error handling
if request.url.path.startswith("/api/"):
    # Return RFC 7807 Problem Details JSON
    return JSONResponse(status_code=..., content=problem_detail)
else:
    # Return HTML error page
    return templates.TemplateResponse(...)
```

### 23. RFC 7807 Problem Details

**Principle**: Use standardized error responses for APIs (RFC 7807 Problem Details for HTTP APIs).

**Structure**:
```json
{
  "type": "https://example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "Feature name cannot be empty",
  "instance": "/api/v1/features",
  "error_code": "VALIDATION_ERROR",
  "fields": {
    "name": "Feature name cannot be empty"
  }
}
```

**Evidence**:
- Git commit `1f80f52` - "Implement RFC 7807 Problem Details error handling"
- `src/presentation/problem_details.py` - Complete implementation
- 6 new tests covering all error scenarios

**Benefits**:
- Machine-readable error format
- Standardized across all APIs
- Field-specific error details
- Programmatic error handling

### 24. Semantic HTTP Status Codes

**Principle**: Use HTTP status codes correctly and consistently.

**Rules**:
- `201 Created` - For POST creating new resources
- `200 OK` - For actions/updates (veto, unveto, merge)
- `204 No Content` - For successful DELETE
- `400 Bad Request` - For validation errors
- `404 Not Found` - For missing resources
- `409 Conflict` - For duplicate creation attempts
- `500 Internal Server Error` - For unexpected errors

**Evidence**:
- `CLAUDE.md:19` - "HTTP status codes: 201 for creation (POST new resources), 200 for actions/updates"
- `src/presentation/api_routes.py` - Consistent status code usage

---

## Documentation Principles

### 25. Requirements Traceability

**Principle**: Link tests to functional requirements via docstrings. Keep requirements close to code.

**Implementation**:
```python
def test_create_property_conflict(session: Session):
    """Test property name uniqueness enforcement.

    Covers:
    - FR-2.3: Property names must be unique within their scope
    - FR-2.4: System prevents duplicate property creation (409 error)
    """
    # Test implementation...
```

**Evidence**:
- `README.md:183-235` - "Requirements Traceability System"
- pytest plugin extracts `FR-X.Y` patterns
- Real-time coverage reporting
- Git-friendly (no external databases)

**Benefits**:
- Requirements live with code (not stale docs)
- Easy to see test coverage
- No enterprise tools required
- Survives refactoring (moves with tests)

### 26. Code is Documentation

**Principle**: Write self-documenting code. Comments explain **why**, not **what**.

**Rules**:
- Type hints document signatures
- Function names describe behavior
- Tests document expected behavior
- Comments explain non-obvious decisions

**Evidence**:
```python
# src/domain/entities.py:32-38 - GOOD: Explains why
# Check for problematic control characters
for char in name:
    if (ord(char) < 32 and char not in [" "]) or ord(char) == 127:
        # Allow space (ord 32), reject control chars and DEL (ord 127)
        raise ValidationError(...)

# BAD: Redundant comment
# Check if name is empty
if not name:
    raise ValidationError("Name cannot be empty")
```

### 27. AI Assistant Instructions in Codebase

**Principle**: Keep AI development guidance in the repository (`CLAUDE.md`) for version control and sharing.

**Evidence**:
- `CLAUDE.md` - Comprehensive AI assistant guidance
- `README.md` - User-facing documentation
- `docs/DEVELOPMENT.md` - Extended technical docs
- `docs/USER-SYSTEM-DESIGN.MD` - Design decision documentation

**Benefits**:
- Versioned with code
- Shared across team
- Searchable and linkable
- Updated with refactorings

---

## Git Workflow Principles

### 28. User Controls Git Operations

**Principle**: AI assistants NEVER execute git commands unless explicitly requested. All git operations are user-initiated.

**Rules**:
- NEVER `git add` automatically
- NEVER `git commit` automatically
- NEVER `git push` automatically
- Only suggest commit messages when asked

**Evidence**:
- `CLAUDE.md:85-94` - "CRITICAL: NO AUTOMATIC GIT OPERATIONS"
- Git commit `9a941ed` - "Clarify git workflow to emphasize user control"

**Rationale**:
- User maintains full control
- Prevents accidental commits
- Allows review before committing
- Respects user workflow preferences

### 29. Git Diff is Authoritative

**Principle**: When suggesting commit messages, describe only what `git diff` shows, not what you think you changed.

**Evidence**:
- `CLAUDE.md:93` - "IMPORTANT: `git diff` is authoritative - only describe changes that actually exist in the git diff"
- Git commit `c17a960` - "Update CLAUDE.md: use git diff as authoritative source"

**Rationale**:
- Prevents hallucinated changes in commit messages
- Ensures accuracy
- Builds trust
- Matches actual diff reviewers see

### 30. Descriptive Commit Messages

**Principle**: Write clear, descriptive commit messages that explain the **what** and **why** of changes.

**Structure**:
```
[One-line summary of change]

[Optional detailed explanation:]
- Bullet points for major changes
- Why the change was needed
- Any important context

[Optional metadata:]
- Related issues/PRs
- Breaking changes
- Migration notes
```

**Evidence**: Review recent commits for examples:
```
commit 1f80f52
Implement RFC 7807 Problem Details error handling with global exception handlers

Add comprehensive error handling system with structured API responses:

- Add RFC 7807 Problem Details implementation for API errors
  - Create ProblemDetail, ValidationProblemDetail, ConflictProblemDetail models
  - Add ProblemDetailFactory for standardized error response creation
  - Include structured error codes for programmatic handling
[... detailed implementation notes ...]
```

---

## Testing Principles

### 31. Fixture-Based Test Isolation

**Principle**: Each test gets a clean database state via pytest fixtures. No shared state between tests.

**Implementation**:
```python
# tests/conftest.py
@pytest.fixture(name="session")
def session_fixture():
    """Provide clean database session for each test."""
    engine = create_test_engine()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
```

**Evidence**:
- `tests/conftest.py` - Comprehensive fixture setup
- Parallel test support with xdist worker isolation

### 32. Parallel Test Execution

**Principle**: Tests must be parallelizable for fast feedback. Use unique databases per worker.

**Implementation**:
```python
# tests/conftest.py - xdist worker isolation
worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")
db_path = f"test_{worker_id}.db"
```

**Evidence**:
- `README.md:117` - `pytest -n10` for parallel execution
- `pyproject.toml:48` - `pytest-xdist==3.8.0` dependency

### 33. Test Coverage as Documentation

**Principle**: Tests document expected behavior. High coverage is a side effect of good tests, not a goal.

**Focus Areas**:
- Happy path scenarios
- Error conditions
- Edge cases
- Requirements coverage (via docstrings)

**Evidence**:
- Comprehensive test suite in `tests/`
- Requirements traceability links
- 111 tests covering domain, application, infrastructure, presentation

---

## Observability Principles

### 34. Structured Logging

**Principle**: Use structured logging with key-value pairs, not string formatting.

**Implementation**:
```python
# GOOD: Structured logging
logger.info("Object created",
    object_name="Pizza",
    object_id=123,
    user="anonymous")

# BAD: String formatting
logger.info(f"Object Pizza (ID 123) created by anonymous")
```

**Evidence**:
- `src/logging_config.py` - structlog configuration
- `src/logging_utils.py` - Shared logging utilities
- `README.md:237-263` - Logging system documentation

**Benefits**:
- Machine-parseable logs
- Easy filtering and aggregation
- Automatic JSON formatting in production
- Rich console output in development

### 35. Telemetry is Opt-In

**Principle**: Observability instrumentation should not pollute development logs. Make it opt-in.

**Evidence**:
- Git commit `aeaa57c` - "Disable verbose OpenTelemetry/SQLAlchemy/aiosqlite logging by default"
- `ENABLE_TELEMETRY` environment flag
- Reduced console noise for better DX

**Rationale**:
- Development experience > telemetry verbosity
- Production enables telemetry
- Local development stays clean
- Easy to debug when needed

### 36. Log Database Operations

**Principle**: Log all database operations (create, update, delete) with structured context.

**Implementation**:
```python
# src/logging_utils.py
def log_database_operation(
    logger: Any,
    operation: str,
    entity_type: str,
    entity_name: str,
    result: str
) -> None:
    """Log database operations with structured context."""
    logger.info(
        f"Database {operation} on {entity_type} {result}",
        operation=operation,
        entity_type=entity_type,
        entity_name=entity_name,
    )
```

**Evidence**:
- Used throughout `src/application/` services
- Consistent logging format
- Audit trail for debugging

---

## Summary Table

| Category | Key Principle | Evidence |
|----------|--------------|----------|
| **Architecture** | Clean layered architecture (DDD) | `src/` structure, commit `730ebbb` |
| **Architecture** | Domain entity purity (zero deps) | `src/domain/entities.py:1-10` |
| **Architecture** | Service functions over classes | `src/application/*.py` |
| **Code Quality** | Modern Python 3.13+ type hints | `pyproject.toml:10`, all source files |
| **Code Quality** | Pinned dependencies with `==` | `pyproject.toml:11-27` |
| **Code Quality** | QA as compass, not gate | `CLAUDE.md:55-69` |
| **Workflow** | UV for all Python operations | `CLAUDE.md:26-28`, commit `d815596` |
| **Workflow** | Reduce redundancy (rr) | Commit `a76c5ac`, `6b57989` |
| **Philosophy** | Simplicity over complexity | Trust-based auth, cookie sessions |
| **Philosophy** | Transparency by default | Veto display, structured logs |
| **Philosophy** | Trust-based collaboration | `docs/USER-SYSTEM-DESIGN.MD` |
| **Tooling** | Modern Python tooling | uv, Ruff, mypy, djLint |
| **Tooling** | Unified QA interface | `uv run qa check` |
| **API Design** | API versioning from day one | `/api/v1/*` prefix |
| **API Design** | RFC 7807 Problem Details | Commit `1f80f52` |
| **Documentation** | Requirements traceability | Test docstrings with `FR-X.Y` |
| **Documentation** | Code is documentation | Type hints, clear names |
| **Git** | User controls git operations | `CLAUDE.md:85-94` |
| **Git** | Git diff is authoritative | `CLAUDE.md:93` |
| **Testing** | Fixture-based isolation | `tests/conftest.py` |
| **Testing** | Parallel test execution | `pytest -n10` |
| **Observability** | Structured logging | `src/logging_config.py` |
| **Observability** | Telemetry is opt-in | `ENABLE_TELEMETRY` flag |

---

## How to Use This Document

### For Developers

1. **Starting a new feature?** Review relevant principles first
2. **Code review?** Check if changes align with these principles
3. **Refactoring?** Use principles as guide for improvements
4. **Unsure about approach?** Find similar patterns in codebase

### For AI Assistants

1. **Before coding** - Review architectural principles
2. **During coding** - Apply code quality and workflow principles
3. **After coding** - Verify against QA and testing principles
4. **Documentation** - Follow documentation principles

### For New Team Members

1. Read this document first
2. Read `README.md` for setup
3. Read `CLAUDE.md` for development workflow
4. Explore codebase to see principles in action

---

## Evolution of Principles

This document captures principles **as of 2025-11-16**. Principles evolve with the codebase.

**Recent Principle Additions**:
- **2025-10-08**: Trust-based user system principles (commit `aeaa57c`)
- **2025-09-23**: RFC 7807 error handling (commit `1f80f52`)
- **2025-09-21**: Soft delete pattern (commit `730ebbb`)

**How Principles Change**:
1. Emerge from practical development
2. Documented in git commits
3. Codified in this document
4. Updated with significant architectural changes

---

## References

- **Architecture Analysis**: `docs/ARCHITECTURE-ANALYSIS.md` (if created by Task agent)
- **User System Design**: `docs/USER-SYSTEM-DESIGN.MD`
- **Development Guide**: `CLAUDE.md`
- **Setup Guide**: `README.md`
- **Git History**: Review commits for design evolution

---

**Last Updated**: 2025-11-16
**Codebase**: SAVT (Suggestion And Veto Tool)
**Python Version**: 3.13+
**Framework**: FastAPI + SQLModel
