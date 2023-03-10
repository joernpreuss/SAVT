from fastapi import FastAPI
from sqlmodel import Session

from database import engine
from models import SVProperty

app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/create/propery/{name}")
async def create_property_anonymously(name: str):
    property = SVProperty(name=name)
    with Session(engine) as session:
        session.add(property)
        session.commit()
    return {"created": {"name": name}}


@app.get("/user/{user}/create/propery/{name}")
async def user_create_property(user: str, name: str):
    property = SVProperty(name=name, created_by=user)
    with Session(engine) as session:
        session.add(property)
        session.commit()
    return {"created": {"name": name}}
