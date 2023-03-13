import sys
from pathlib import Path

from fastapi import FastAPI

sys.path.append(str(Path(__file__).parent))
from routes import router

app = FastAPI()
app.include_router(router)
