import socket
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings
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
from .presentation.routes import router


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

# Add request logging middleware
app.middleware("http")(log_requests_middleware)

# Include routers
app.include_router(api_router)
app.include_router(router)
