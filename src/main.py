import sys
from contextlib import asynccontextmanager
from pathlib import Path

# import logging
from fastapi import FastAPI

sys.path.append(str(Path(__file__).parent))
from api_routes import api_router
from config import settings
from database import get_main_engine, init_db
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema once at startup
    init_db(get_main_engine())
    # Print hostname and IP once on startup (also runs under TestClient)
    import socket

    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    print("Your Computer Name is: " + hostname)
    print("Your Computer IP Address is: " + ip_addr)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    debug=settings.debug,
    lifespan=lifespan,
)
app.include_router(api_router)
app.include_router(router)

# logger = logging.getLogger(__name__)
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.DEBUG)
# logger.info("test asdfg")
