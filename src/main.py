import sys
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from jinja2 import Environment
from sqlmodel import select  # type: ignore
from sqlmodel import Session

sys.path.append(str(Path(__file__).parent))
from database import get_engine, init_db
from models import SVProperty

app = FastAPI()
environment = Environment()


def get_main_engine():
    engine = get_engine(db_name="pytest")
    init_db(engine)
    return engine


def get_session():
    with Session(get_main_engine()) as session:
        yield session


@app.get("/api/")
async def api_root():
    return {"Hello": "World"}


@app.get("/api/create/property/{name}")
async def api_create_property_anonymously(
    *, session: Session = Depends(get_session), name: str
):
    property = SVProperty(name=name)
    session.add(property)
    session.commit()
    return {"created": {"name": name}}


@app.get("/api/user/{user}/create/property/{name}")
async def api_user_create_property(
    *, session: Session = Depends(get_session), user: str, name: str
):
    property = SVProperty(name=name, created_by=user)

    session.add(property)
    session.commit()

    session.refresh(property)
    # TODO error handling
    return {"created": property.dict()}


@app.get("/api/user/{user}/veto/property/{name}")
async def api_user_veto_property(
    *, session: Session = Depends(get_session), user: str, name: str
):

    statement = select(SVProperty).where(SVProperty.name == name)
    results = session.exec(statement)
    property = results.one()

    if property:
        if user not in property.vetoed_by:
            property.vetoed_by = property.vetoed_by + [user]

        session.commit()
        session.refresh(property)

        return {"vetoed": property.dict()}
    else:
        return {"error": f'property "{name}" not found'}


@app.get("/api/list/properties")
async def api_list_properties(*, session: Session = Depends(get_session)):
    statement = select(SVProperty)
    results = session.exec(statement)
    properties = results.all()

    return {
        "properties": sorted(
            [
                {
                    "name": property.name,
                    "vetoed": len(property.vetoed_by) > 0,
                }
                for property in properties
            ],
            key=lambda x: x["vetoed"],
        )
    }


@app.get("/", response_class=HTMLResponse)
async def list_properties_html(*, session: Session = Depends(get_session)):
    statement = select(SVProperty)
    results = session.exec(statement)
    properties = results.all()

    title = "Properties"

    html = r"""
        <html>
            <head>
                <title>{{title}}</title>
            </head>
            <body>
                <h1>{{title}}</h1>
                {% for property in properties %}
                    <p>{{property.name}}</p>
                {% endfor %}.
            </body>
        </html>
    """

    return environment.from_string(html).render(
        title=title,
        properties=properties,
    )
