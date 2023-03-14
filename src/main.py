import sys
from pathlib import Path

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
