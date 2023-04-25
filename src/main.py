import sys
from pathlib import Path

# import logging
from debug_toolbar.middleware import DebugToolbarMiddleware
from fastapi import FastAPI

sys.path.append(str(Path(__file__).parent))
from api_routes import api_router
from routes import router

app = FastAPI(debug=True)
app.include_router(api_router)
app.include_router(router)
app.add_middleware(
    DebugToolbarMiddleware,
    panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"],
)

# logger = logging.getLogger(__name__)
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.DEBUG)
# logger.info("test asdfg")


def show_local_ip():
    import socket

    hostname = socket.gethostname()
    ip_addr = socket.gethostbyname(hostname)
    print("Your Computer Name is: " + hostname)
    print("Your Computer IP Address is: " + ip_addr)


show_local_ip()
