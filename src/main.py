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
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add request logging middleware
app.middleware("http")(log_requests_middleware)

# Include routers
app.include_router(api_router)
app.include_router(router)
