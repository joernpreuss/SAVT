# SAVT Architecture Analysis

## Overview

SAVT implements a **clean, layered architecture** with clear separation of concerns and explicit dependency flow. The project demonstrates domain-driven design principles with a trust-based approach to user interactions.

---

## 1. Layered Architecture Implementation

### Directory Structure

```
src/
├── domain/                    # Pure business logic (no dependencies)
│   ├── entities.py           # Dataclass-based domain models
│   ├── exceptions.py         # Domain-specific exceptions
│   └── constants.py          # Business rule constants
├── application/              # Business logic & services
│   ├── item_service.py       # Item CRUD operations
│   ├── feature_service.py    # Feature CRUD & veto operations
│   ├── item_operations_service.py  # Complex operations (merge/split/move)
│   └── validation.py         # Shared validation utilities
├── infrastructure/           # Database & external dependencies
│   └── database/
│       ├── models.py         # SQLModel persistence models
│       └── database.py       # Database engine & session management
└── presentation/             # API & web routes
    ├── api_routes.py         # JSON API endpoints (REST)
    ├── routes.py             # HTML routes (Jinja2 + HTMX)
    ├── error_handlers.py     # Centralized error handling
    └── problem_details.py    # RFC 7807 error responses
```

### Layer Responsibilities

#### **Domain Layer** (`src/domain/`)
Pure business entities with **zero external dependencies**.

**Key Pattern: Dataclass with Post-Init Validation**
```python
# src/domain/entities.py
@dataclass
class Item:
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
        if self.kind and len(self.kind) > MAX_KIND_LENGTH:
            raise ValidationError(...)

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        self.deleted_at = datetime.now()
```

**Key Pattern: Feature Veto Transparency**
```python
@dataclass
class Feature:
    id: int | None
    name: str
    amount: int = 1
    created_by: str | None = None
    deleted_at: datetime | None = None
    vetoed_by: list[str] | None = None  # <-- Stores WHO vetoed, not just count
    item_id: int | None = None

    def add_veto(self, user: str) -> None:
        if self.vetoed_by is None:
            self.vetoed_by = []
        if user not in self.vetoed_by:
            self.vetoed_by.append(user)

    def is_vetoed_by(self, user: str) -> bool:
        return user in (self.vetoed_by or [])
```

**Domain Constants Encapsulation**
```python
# src/domain/constants.py
from typing import Final

MAX_NAME_LENGTH: Final = 100
MAX_KIND_LENGTH: Final = 50
MAX_FEATURE_AMOUNT: Final = 3
```

#### **Application Layer** (`src/application/`)
Business logic orchestration with **database access only** via session dependency injection.

**Key Pattern: Service Functions with Explicit Dependencies**
```python
# src/application/item_service.py
def create_item(session: Session, item: Item) -> Item:
    logger.debug("Creating item", item_name=item.name)
    
    # Validate using domain rules
    validate_entity_name_with_logging(item.name, "item")
    
    # Check for duplicates
    same_name_item: Final = get_item(session, item.name)
    if not same_name_item:
        commit_and_refresh_entity(session, item)  # Shared utility
        log_database_operation(...)  # Logging as cross-cutting concern
        return item
    else:
        raise ItemAlreadyExistsError(...)
```

**Key Pattern: Domain → Database Conversion**
Services work with domain entities (`src/domain/entities.py`) and convert to/from database models:
```python
# Inside item_service.py
def delete_item(session: Session, item_name: str) -> bool:
    item: Final = get_item(session, item_name)
    
    # Convert to domain entity and perform soft delete
    domain_item = item.to_domain()
    domain_item.soft_delete()
    
    # Update the database model
    item.deleted_at = domain_item.deleted_at
    session.add(item)
    session.commit()
```

**Key Pattern: Async/Sync Parallel Implementation**
Both sync and async versions of critical operations:
```python
# src/application/item_service.py - Sync version
def get_items(session: Session) -> Sequence[Item]:
    statement: Final = select(Item).where(Item.deleted_at.is_(None))
    results: Final = session.exec(statement)
    items: Final = results.all()
    for item in items:
        item.features = [f for f in item.features if f.deleted_at is None]
    return items

# Async version for better concurrency
async def get_items_async(session: AsyncSession) -> Sequence[Item]:
    statement: Final = select(Item).where(Item.deleted_at.is_(None))
    result = await session.execute(statement)
    items = result.scalars().all()
    for item in items:
        item.features = [f for f in item.features if f.deleted_at is None]
    return items
```

**Key Pattern: Shared Validation Utilities**
Consolidates common validation logic to prevent duplication:
```python
# src/application/validation.py
def validate_entity_name_with_logging(name: str, entity_type: str = "entity") -> None:
    """Validate entity name with logging for application layer."""
    try:
        validate_entity_name(name, entity_type)  # Call domain validator
    except ValidationError as e:
        # Log specific validation failures
        if "empty" in str(e):
            logger.warning(f"{entity_type.title()} creation failed - empty name provided", ...)
        raise ValueError(str(e)) from e

def commit_and_refresh_entity[T: SQLModel](session: Session, entity: T) -> T:
    """Common pattern for committing and refreshing entities."""
    session.add(entity)
    session.commit()
    session.refresh(entity)
    return entity
```

#### **Infrastructure Layer** (`src/infrastructure/`)
Database persistence and external system integration.

**Key Pattern: SQLModel Bridge Between Layers**
```python
# src/infrastructure/database/models.py
class Item(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=MAX_NAME_LENGTH)
    kind: str | None = Field(default=None, max_length=MAX_KIND_LENGTH)
    created_by: str | None = None
    deleted_at: datetime | None = Field(default=None, index=True)
    
    features: list["Feature"] = Relationship(back_populates="item")
    
    @classmethod
    def from_domain(cls, domain_item: DomainItem) -> "Item":
        """Convert domain entity to persistence model."""
        return cls(
            id=domain_item.id,
            name=domain_item.name,
            kind=domain_item.kind,
            created_by=domain_item.created_by,
            deleted_at=domain_item.deleted_at,
        )
    
    def to_domain(self) -> DomainItem:
        """Convert persistence model to domain entity."""
        return DomainItem(
            id=self.id,
            name=self.name,
            kind=self.kind,
            created_by=self.created_by,
            deleted_at=self.deleted_at,
        )
```

**Key Pattern: JSON Column for Veto Transparency**
Stores list of who vetoed (not just count) using SQLModel's JSON support:
```python
class Feature(SQLModel, table=True):
    # ...
    vetoed_by: list[str] = Field(default_factory=list, sa_column=Column(JSON))
```

**Key Pattern: Engine & Session Management**
Separate engines for sync/async with optimized pooling:
```python
# src/infrastructure/database/database.py
def _get_engine() -> Engine:
    database_url = settings.effective_database_url
    if "sqlite" in database_url:
        return create_engine(database_url, 
                            connect_args={"check_same_thread": False},
                            poolclass=StaticPool)
    elif "postgresql" in database_url:
        return create_engine(database_url,
                            pool_pre_ping=True,
                            pool_size=10,
                            max_overflow=20)

def _get_async_engine() -> AsyncEngine:
    """Create async engine with optimized connection pooling."""
    if "postgresql" in database_url:
        return create_async_engine(async_url,
                                  pool_size=20,     # Core connections
                                  max_overflow=15,  # Peak connections
                                  pool_recycle=3600,
                                  pool_pre_ping=True)
```

#### **Presentation Layer** (`src/presentation/`)
API routes and web UI, with centralized error handling.

**Key Pattern: Dual API + HTML Routes**
```python
# src/presentation/api_routes.py - REST API with Pydantic models
api_router: Final = APIRouter(
    prefix="/api/v1",  # API versioning for future compatibility
    tags=["features", "items"],
    responses={400: {...}, 404: {...}, 409: {...}, 422: {...}}
)

@api_router.post("/users/{user}/properties")
def create_feature_api(
    user: str,
    feature: FeatureName,
    session: Session = Depends(get_session),
):
    # Returns JSON with RFC 7807 Problem Details for errors
```

```python
# src/presentation/routes.py - Server-side rendered HTML with HTMX
router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")

@router.post("/create-item", response_class=HTMLResponse)
async def create_item_route(
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    # Returns HTML for HTMX dynamic interactions
```

**Key Pattern: Centralized Error Handling**
Single source of truth for error formatting and conversion:
```python
# src/presentation/error_handlers.py
class ErrorFormatter:
    @staticmethod
    def format_user_friendly_message(error: Exception, ...) -> str:
        """Convert technical errors to user-friendly messages."""
        if isinstance(error, ItemAlreadyExistsError):
            return f"A {settings.object_name_singular} with that name already exists..."
        elif isinstance(error, ValidationError):
            error_msg = str(error)
            if "name cannot be empty" in error_msg.lower():
                return "Please enter a name for the..."
            # ... more error handling

def handle_domain_error(error: DomainError, request: Request) -> JSONResponse:
    """Convert domain errors to appropriate HTTP responses."""
    user_message = ErrorFormatter.format_user_friendly_message(error)
    
    # Check if API or HTML request
    if request.url.path.startswith("/api/"):
        # Return RFC 7807 Problem Details for API
        problem = ProblemDetailFactory.resource_already_exists(...)
        return JSONResponse(status_code=problem.status, content=...)
    else:
        # Return HTTPException for HTML
        raise HTTPException(status_code=409, detail=user_message)
```

---

## 2. Dependency Flow

### Unidirectional Dependency Graph

```
Presentation Layer
    ↓
Application Layer
    ↓
Infrastructure Layer (Database)

Domain Layer ← Referenced by all layers but has NO dependencies
```

### Explicit Dependency Injection

**Session Dependency Pattern**
```python
# FastAPI route with dependency injection
@router.post("/create-item")
def create_item(
    request: Request,
    session: Session = Depends(get_session),  # Injected by FastAPI
):
    item = Item(name=request.form["name"])
    create_item(session, item)  # Passes to service
```

**Database Factory Pattern**
```python
# src/infrastructure/database/database.py
_engine: Engine | None = None

def get_main_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine

def get_session() -> Generator[Session]:
    with Session(get_main_engine()) as session:
        yield session  # FastAPI auto-closes when route completes
```

### Cross-Cutting Concerns

Handled via utilities and middleware, not pollution of core layers:

```python
# Logging as utility function (not mixed into domain)
from ..logging_utils import log_database_operation, log_user_action

def create_feature(session: Session, feature: Feature) -> tuple[Feature, str | None]:
    # ... business logic ...
    log_database_operation(
        operation="create",
        table="Feature",
        success=True,
        feature_name=feature.name,
        feature_id=feature.id,
    )
    log_user_action(
        action="create_feature",
        user=feature.created_by,
        feature_name=feature.name,
    )
```

```python
# Middleware for rate limiting and request logging
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(log_requests_middleware)
```

---

## 3. Code Organization Patterns

### Service Functions vs Classes

The codebase uses **module-level functions** for services, not classes:

```python
# src/application/feature_service.py
def create_feature(session: Session, feature: Feature) -> tuple[Feature, str | None]:
    ...

def get_features(session: Session) -> Sequence[Feature]:
    ...

def veto_item_feature(session: Session, user: str, name: str, ...) -> Feature | None:
    ...
```

**Rationale**: 
- Functions are more testable than class methods
- No stateful service instances needed
- Clear function signatures show dependencies
- Easier to reason about side effects

### Entity-Driven Naming

Services are organized around **domain concepts**, not operations:
- `item_service.py` - All Item operations (CRUD, delete, restore)
- `feature_service.py` - All Feature operations (CRUD, veto, unveto)
- `item_operations_service.py` - Complex multi-entity operations (merge, split, move)

### Validation Layering

**Three levels of validation with clear responsibility**:

1. **Domain Layer** - Pure validation without dependencies
```python
# src/domain/entities.py
def validate_entity_name(name: str, entity_type: str = "entity") -> None:
    """Validate entity name according to domain business rules."""
    if not name or not name.strip():
        raise ValidationError(f"{entity_type.title()} name cannot be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise ValidationError(f"... name cannot be longer than {MAX_NAME_LENGTH} characters")
```

2. **Application Layer** - Domain validation with logging
```python
# src/application/validation.py
def validate_entity_name_with_logging(name: str, entity_type: str = "entity") -> None:
    """Validate entity name with logging for application layer."""
    try:
        validate_entity_name(name, entity_type)  # Call domain validator
    except ValidationError as e:
        if "empty" in str(e):
            logger.warning(f"{entity_type.title()} creation failed - empty name provided", ...)
        raise ValueError(str(e)) from e  # Convert for backward compatibility
```

3. **Presentation Layer** - Database model validation + error formatting
```python
# src/infrastructure/database/models.py
class Item(SQLModel, table=True):
    name: str = Field(index=True, min_length=1, max_length=MAX_NAME_LENGTH)
    
# src/presentation/error_handlers.py
def format_user_friendly_message(error: Exception, ...) -> str:
    """Convert technical errors to user-friendly messages."""
    if "name cannot be empty" in error_msg.lower():
        return "Please enter a name for the item."
```

### Soft Delete Pattern

Consistently implemented across entities:

```python
# Domain entity
def soft_delete(self) -> None:
    self.deleted_at = datetime.now()

def is_deleted(self) -> bool:
    return self.deleted_at is not None

# Service layer applies it
def delete_item(session: Session, item_name: str) -> bool:
    domain_item = item.to_domain()
    domain_item.soft_delete()          # Use domain logic
    item.deleted_at = domain_item.deleted_at  # Update DB model
    session.add(item)
    session.commit()

# Queries filter by default
statement: Final = select(Item).where(Item.deleted_at.is_(None))
```

### ID-Based Reference

Features use `feature.id` for veto operations, not `feature.name`, enabling duplicate names:

```python
# src/application/feature_service.py
def veto_feature_by_id(
    session: Session, user: str, feature_id: int, veto: bool = True
) -> Feature | None:
    feature = get_feature_by_id(session, feature_id)
    if feature:
        apply_veto_to_feature(session, feature, user, veto, feature_id=feature_id)
    return feature
```

---

## 4. Testing Patterns

### Test Structure

```
tests/
├── conftest.py                        # Shared fixtures
├── test_service.py                    # Application layer tests
├── test_api.py                        # API endpoint tests
├── test_frontend.py                   # HTML route tests
├── test_error_handling.py             # Error response tests
├── test_character_validation.py       # Validation tests
├── test_async_operations.py           # Async operation tests
└── test_htmx_interactions.py          # HTMX interaction tests
```

### Fixture Pattern - Database Isolation

```python
# tests/conftest.py
@pytest.fixture(name="session")
def session_fixture():
    database_url = _get_test_database_url()
    
    if database_url.startswith("postgresql"):
        # PostgreSQL for integration tests with parallel support
        engine = create_engine(database_url, pool_pre_ping=True, ...)
    else:
        # SQLite in-memory for unit tests
        engine = create_engine(database_url, 
                              connect_args={"check_same_thread": False},
                              poolclass=StaticPool)
    
    SQLModel.metadata.create_all(engine)
    
    with TestSession(engine) as session:
        yield session  # Test uses this session
        # Cleanup automatic
```

### Parallel Test Support

```python
def _get_test_database_url() -> str:
    """Get database URL for testing based on environment."""
    if os.getenv("TEST_DATABASE") == "postgresql":
        # For parallel tests, use unique database name per worker
        worker_id = os.getenv("PYTEST_XDIST_WORKER", "main")
        
        # Replace only the database name at the end of the URL
        if base_url.endswith("/savt"):
            return base_url[:-5] + f"/savt_test_{worker_id}"
```

### Async Test Support

```python
# tests/conftest.py
@pytest.fixture(name="async_session")
async def async_session_fixture():
    """Async session fixture for testing async database operations."""
    database_url = _get_async_test_database_url()
    
    async with AsyncSession(async_engine) as session:
        yield session
```

### Test Organization - Requirements Traceability

```python
# tests/test_service.py
def test_create_item_with_feature(session: Session, timestamp_str: str):
    """Test item and feature creation.
    
    Covers:
    - FR-1.1: Users can create items with unique names
    - FR-2.1: Users can create features with names
    - FR-2.2: Features can be associated with items
    """
    item = Item(name=f"test_item_{timestamp_str}")
    create_item(session, item)
    assert item.id is not None
```

### API Client Testing

```python
# tests/test_api.py
@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    # Override FastAPI dependency
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_create_feature(client: TestClient, timestamp_str: str):
    response = client.post(
        "/api/v1/users/test_user/properties",
        json={"name": f"test_feature_{timestamp_str}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "created" in data
```

### Feature Combination Testing

```python
def test_create_feature_combination(session: Session, timestamp_str: str):
    """Test that duplicate feature names are combined instead of creating duplicates."""
    name = f"feature_{timestamp_str}"
    f1, msg1 = create_feature(session, Feature(name=name, amount=1))
    f2, msg2 = create_feature(session, Feature(name=name, amount=1))
    
    assert f1.id == f2.id        # Same ID - combined, not separate
    assert f2.amount == 2        # Amount should be combined (1 + 1 = 2)
    assert msg1 is None          # No message for first creation
    assert msg2 is None          # No capping occurred
```

### Async Rate Limiting Fixture

```python
@pytest.fixture(autouse=True)
def disable_rate_limiting_for_tests():
    """Disable rate limiting for most tests to avoid interference."""
    from src.rate_limiting import rate_limiter
    
    rate_limiter.reset()
    rate_limiter.disable()
    
    yield
    
    rate_limiter.enable()
    rate_limiter.reset()
```

---

## 5. Notable Design Decisions

### A. User System Design - Trust-Based, No Auth

**Decision**: Lightweight, cookie-based user identification without authentication.

```python
# src/presentation/routes.py
def _get_next_default_item_name(session: Session, username: str = "anonymous") -> str:
    """Get the next available {object_name}-{user#}-{N} name."""
    base_name = settings.object_name_singular.title()
    
    # Extract user number from username (e.g., "User-1" -> "1")
    user_match = re.match(r"^User-(\d+)$", username)
    if user_match:
        user_identifier = user_match.group(1)
    else:
        # For custom usernames, use first 5 chars as identifier
        user_identifier = username[:5]
    
    # Count how many items this user has created
    counter = 1
    while True:
        candidate_name = f"{base_name}-{user_identifier}-{counter}"
        if get_item(session, candidate_name) is None:
            return candidate_name
        counter += 1
```

**Rationale**: Trust-based for collaborative internal use, auto-generated user IDs for privacy.

### B. Veto Transparency - Who Over Count

**Decision**: Store `vetoed_by: list[str]` instead of `veto_count: int`.

**Benefits**:
- Know who vetoed (transparency)
- Detect if a user changed their mind (remove from list on unveto)
- Enable veto notifications to specific users
- Audit trail of veto history

```python
# Domain entity supports:
feature.is_vetoed_by("Alice")      # Direct check
feature.add_veto("Alice")          # Add veto
feature.remove_veto("Alice")       # Remove veto (unveto)
feature.is_vetoed()                # Check if any veto exists
```

### C. API Versioning from Day One

```python
# src/presentation/api_routes.py
api_router: Final = APIRouter(
    prefix="/api/v1",  # <-- Explicit versioning
    tags=["features", "items"],
)
```

**Rationale**: Easy to introduce `/api/v2` without breaking existing clients.

### D. RFC 7807 Problem Details for API Errors

```python
# src/presentation/problem_details.py
class ProblemDetail(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str | None = None

class ValidationProblemDetail(ProblemDetail):
    errors: list[dict[str, str]] = []  # Field-level errors

# Applied in error handling
if request.url.path.startswith("/api/"):
    problem = ProblemDetailFactory.validation_failed(
        detail=user_message,
        instance=str(request.url.path),
        field_errors=field_errors,
    )
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
    )
```

**Rationale**: Standard error format for API clients, consistent with HTTP spec.

### E. Dual Sync/Async Operations

**Decision**: Both sync and async versions of database operations.

```python
# Sync version
def get_items(session: Session) -> Sequence[Item]:
    statement = select(Item).where(Item.deleted_at.is_(None))
    return session.exec(statement).all()

# Async version
async def get_items_async(session: AsyncSession) -> Sequence[Item]:
    statement = select(Item).where(Item.deleted_at.is_(None))
    result = await session.execute(statement)
    return result.scalars().all()
```

**Rationale**: 
- Sync for simpler HTML routes
- Async for API routes handling concurrent requests
- Flexibility to optimize each path independently

### F. Smart Name Truncation for Merged Items

```python
# src/utils.py
def smart_shorten_name(name: str, max_length: int = MAX_NAME_LENGTH) -> str:
    """Intelligently shorten complex merged names with better logic.
    
    Handles cases like "TestPizza2-1-TestPizza1-3-TestPizza1-2" by:
    1. Detecting repeated base names and consolidating them
    2. Using abbreviations for common patterns
    3. Falling back to regular truncation if needed
    """
    # Strategy 1: Try to consolidate repeated names
    # "TestPizza2-1-TestPizza1-3-TestPizza1-2" -> "TestPizza+3merged"
    shortened = _consolidate_repeated_names(name, max_length)
    if len(shortened) <= max_length:
        return shortened
    
    # Strategy 2: Use abbreviations for common patterns
    # "VeryLongPizzaNameHere-Merge-AnotherLong" -> "VLPNameHere+ALong"
    shortened = _abbreviate_long_parts(name, max_length)
    if len(shortened) <= max_length:
        return shortened
    
    # Strategy 3: Fall back to regular truncation
    return truncate_name(name, max_length)
```

**Rationale**: Merge operations can create complex names; smart truncation preserves meaning.

### G. Centralized Veto Application Logic

```python
# src/utils.py
def apply_veto_to_feature(
    session,
    feature,
    user: str,
    veto: bool,
    item_name: str | None = None,
    feature_id: int | None = None,
) -> bool:
    """Apply veto/unveto logic to a feature and handle all database/logging operations."""
    action = "veto" if veto else "unveto"
    
    vetoed_by_set = set(feature.vetoed_by)
    original_vetoed_by = set(feature.vetoed_by)
    
    if veto:
        vetoed_by_set.add(user)
    else:
        vetoed_by_set.discard(user)
    
    # Only update if there's a change
    if original_vetoed_by != vetoed_by_set:
        feature.vetoed_by = sorted(vetoed_by_set)
        session.commit()
        session.refresh(feature)
        
        log_database_operation(...)
        log_user_action(...)
        return True
    else:
        logger.debug("No change needed for action", ...)
        return False
```

**Rationale**: DRY principle - reused by both name-based and ID-based veto operations.

### H. Settings-Driven Terminology

```python
# src/config.py
settings.object_name_singular = "Item"      # "Pizza"
settings.object_name_plural = "Items"       # "Pizzas"
settings.property_name_singular = "Feature" # "Topping"
settings.property_name_plural = "Features"  # "Toppings"
```

Used in:
```python
# src/presentation/error_handlers.py
def format_user_friendly_message(error: Exception, ...) -> str:
    if isinstance(error, ItemAlreadyExistsError):
        return (
            f"A {settings.object_name_singular} with that name already exists. "
            "Please choose a different name."
        )
```

**Rationale**: Domain-agnostic terminology allows reusing SAVT for any decision context.

### I. HTTP Status Code Semantics

```python
# 201 Created for creating new resources (POST that creates)
# 200 OK for actions/updates (veto, unveto, merge, split)

@api_router.post("/users/{user}/properties", status_code=201)
async def create_feature(...)

@api_router.post("/features/{feature_id}/veto", status_code=200)
async def veto_feature(...)
```

**Rationale**: Follows REST conventions: 201 for resource creation, 200 for state changes.

### J. Type Hints with Modern Python Syntax

```python
# Uses Python 3.13 modern syntax
name: str | None              # Not Optional[str]
amounts: list[str]            # Not List[str]
result: dict[str, int]        # Not Dict[str, int]

def get_or_default[T](items: list[T], default: T) -> T:  # PEP 695 generics
    return items[0] if items else default
```

**Rationale**: Cleaner, more readable, aligned with Python 3.13+ standards.

---

## Summary of Architectural Strengths

| Aspect | Pattern | Benefit |
|--------|---------|---------|
| **Separation of Concerns** | Domain → App → Infra → Presentation | Easy to test, modify, understand |
| **Dependency Flow** | Unidirectional, explicit injection | No circular dependencies, clear data flow |
| **Error Handling** | Centralized, layered validation | Consistent error messages, RFC 7807 compliance |
| **Entity Management** | Dataclass + post-init validation | Pure domain logic, self-validating |
| **Concurrency** | Dual sync/async operations | Flexibility for different request patterns |
| **Database Abstraction** | SQLModel bridge with `to_domain()/from_domain()` | Clean separation, easy to swap databases |
| **Testing** | Fixture-based, parallel-safe, async-capable | Comprehensive coverage, fast CI/CD |
| **Veto Transparency** | `vetoed_by: list[str]` instead of count | Enables audit trail, transparency, unveto |
| **Soft Deletes** | Consistent pattern across all entities | Non-destructive, audit-friendly |
| **Logging** | Utility-based, not mixed into domain | Clean separation, flexible logging strategies |

