import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.append(str(Path(__file__).parent))
from api_routes import api_router
from routes import router


app = FastAPI()
app.include_router(api_router)
app.include_router(router)
