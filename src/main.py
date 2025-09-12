import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api_routes import api_router
from .config import settings
from .database import get_main_engine, init_db
from .logging_config import get_logger, setup_logging
from .logging_utils import log_system_info
from .middleware import log_requests_middleware
from .routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)

    # Initialize database schema once at startup
    init_db(get_main_engine())
    logger.info("Database initialized successfully")

    # Log system info instead of print statements
    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    log_system_info(hostname, ip_addr, settings.debug)

    yield

    logger.info("Application shutdown completed")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Add request logging middleware
app.middleware("http")(log_requests_middleware)

# Include routers
app.include_router(api_router)
app.include_router(router)
