import socket
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .config import settings
from .domain.exceptions import DomainError
from .infrastructure.database.database import (
    get_async_engine,
    get_main_engine,
    init_async_db,
    init_db,
)
from .logging_config import get_logger, setup_logging
from .logging_utils import log_system_info
from .middleware import log_requests_middleware
from .presentation.api_routes import api_router
from .presentation.error_handlers import handle_domain_error, handle_validation_error
from .presentation.problem_details import ProblemDetailFactory
from .presentation.routes import router
from .rate_limiting import rate_limit_middleware
from .telemetry import setup_telemetry


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)

    # Initialize database schema once at startup
    # Use async database initialization for better concurrency support
    try:
        await init_async_db(get_async_engine())
        logger.info("Async database initialized successfully")
    except Exception as e:
        logger.warning(f"Async database init failed, falling back to sync: {e}")
        init_db(get_main_engine())
        logger.info("Sync database initialized successfully")

    # Log system info instead of print statements
    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    log_system_info(hostname, ip_addr, settings.debug)

    yield

    logger.info("Application shutdown completed")


app: Final = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
    description="""
**SAVT (Suggestion And Veto Tool)** - Pure Python collaborative decision-making
platform for any group decision.

## Use Cases

From simple choices to complex business decisions:
- **Team decisions** (meeting times, project priorities, vendor selection)
- **Development workflows** (code reviews, deployments, architecture choices)
- **Social planning** (restaurant choices, event planning, group activities)
- **Business operations** (budget allocation, policy changes, hiring decisions)

## Core Features

- **Democratic suggestion system** - Anyone can propose options
- **Veto-based consensus** - Participants can block options they strongly oppose
- **Real-time collaboration** with HTMX-powered UI
- **Persistent undo** functionality for mistake recovery
- **Comprehensive REST API** for integration with external systems

## API Integration

This REST API enables programmatic integration with SAVT for:
- **Automated decision workflows** (deployment approvals, release gates)
- **External system integration** (Slack bots, workflow tools, dashboards)
- **Custom UI development** and mobile applications
- **Bulk operations** and reporting for analytics

## Rate Limiting

API endpoints are rate limited for stability and fair usage:
- **General endpoints**: 100 requests per minute per IP
- **Write operations**: 30 requests per minute per IP
- **Bulk operations**: 10 requests per minute per IP

Rate limit headers (`X-RateLimit-*`) are included in all API responses.

## Authentication

Currently, user identification is handled via simple string usernames.
Future versions will include proper authentication and authorization.
    """.strip(),
    contact={
        "name": "SAVT API Support",
        "url": "https://github.com/savt/issues",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "features",
            "description": "Manage decision features/properties that can be "
            + "suggested and vetoed",
        },
        {
            "name": "items",
            "description": "Manage decision items that contain multiple features",
        },
        {
            "name": "users",
            "description": "User-specific operations for creating and voting on "
            + "features",
        },
    ],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup OpenTelemetry tracing
setup_telemetry(app)

# Add middleware (order matters: rate limiting before logging)
app.middleware("http")(rate_limit_middleware)
app.middleware("http")(log_requests_middleware)


# Add global exception handlers
@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    """Global handler for domain-specific errors."""
    logger = get_logger(__name__)
    logger.warning(
        "Domain error occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return handle_domain_error(exc, request)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Global handler for validation errors."""
    logger = get_logger(__name__)
    logger.warning(
        "Validation error occurred",
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
    )
    return handle_validation_error(exc, request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Global handler for Pydantic validation errors."""
    logger = get_logger(__name__)
    logger.warning(
        "Request validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method,
    )

    if request.url.path.startswith("/api/"):
        # Convert Pydantic errors to Problem Details format
        field_errors = []
        for error in exc.errors():
            field_name = ".".join(str(loc) for loc in error["loc"] if loc != "body")
            field_errors.append(
                {
                    "field": field_name or "unknown",
                    "code": error["type"],
                    "message": error["msg"],
                }
            )

        problem = ProblemDetailFactory.validation_failed(
            detail="Request validation failed",
            instance=str(request.url.path),
            field_errors=field_errors,
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(exclude_none=True),
        )
    else:
        # For HTML requests, return a user-friendly error
        from .presentation.error_handlers import render_error_response

        return render_error_response(
            request, "Please check your input and try again.", status_code=422
        )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """Global handler for database errors."""
    logger = get_logger(__name__)
    logger.error(
        "Database error occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    if request.url.path.startswith("/api/"):
        if isinstance(exc, IntegrityError):
            # Handle database constraint violations
            problem = ProblemDetailFactory.resource_already_exists(
                resource_type="resource",
                detail="A resource with these values already exists",
                instance=str(request.url.path),
            )
        else:
            problem = ProblemDetailFactory.internal_server_error(
                detail="A database error occurred. Please try again.",
                instance=str(request.url.path),
            )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(exclude_none=True),
        )
    else:
        from .presentation.error_handlers import render_error_response

        return render_error_response(
            request, "A database error occurred. Please try again.", status_code=500
        )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global handler for unexpected errors."""
    logger = get_logger(__name__)
    logger.error(
        "Unexpected error occurred",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    if request.url.path.startswith("/api/"):
        problem = ProblemDetailFactory.internal_server_error(
            detail="An unexpected error occurred. Please try again.",
            instance=str(request.url.path),
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(exclude_none=True),
        )
    else:
        from .presentation.error_handlers import render_error_response

        return render_error_response(
            request, "Something went wrong. Please try again.", status_code=500
        )


# Include routers
app.include_router(api_router)
app.include_router(router)
