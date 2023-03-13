import logging
import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select  # type: ignore
from sqlmodel import Session

sys.path.append(str(Path(__file__).parent))
from database import get_engine, init_db
from models import SVProperty

# logger
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)

# app
app = FastAPI()

# templates
templates = Jinja2Templates(directory="templates/")


def get_main_engine():
    engine = get_engine(db_name="prod")
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
    *,
    session: Session = Depends(get_session),
    name: str,
):
    property = SVProperty(name=name)
    session.add(property)
    session.commit()
    return {"created": {"name": name}}


@app.get("/api/user/{user}/create/property/{name}")
async def api_user_create_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    property = SVProperty(name=name, created_by=user)

    session.add(property)
    session.commit()

    session.refresh(property)

    # TODO error handling
    return {"created": property.dict()}


def veto(
    session: Session,
    user: str,
    name: str,
):
    statement = select(SVProperty).where(SVProperty.name == name)
    results = session.exec(statement)
    property = results.one()

    if property:
        if user not in property.vetoed_by:
            property.vetoed_by = property.vetoed_by + [user]

        session.commit()
        session.refresh(property)

    return property


@app.get("/api/user/{user}/veto/property/{name}")
async def api_user_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    property = veto(session, user, name)

    if property:
        return {"vetoed": property.dict()}

    else:
        return {"error": f'property "{name}" not found'}


@app.get("/user/{user}/veto/property/{name}")
async def user_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):

    #  property =
    veto(session, user, name)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.get("/api/list/properties")
async def api_list_properties(
    *,
    session: Session = Depends(get_session),
):
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
            key=lambda x: x["vetoed"],  # sort by "vetoed"
        )
    }


@app.get("/", response_class=HTMLResponse)
async def list_properties_html(
    *,
    session: Session = Depends(get_session),
    request: Request,
):
    statement = select(SVProperty)
    results = session.exec(statement)
    properties = results.all()

    response = templates.TemplateResponse(  # type: ignore
        "properties.html",
        {
            "properties": [
                {
                    "name": property.name,
                    "vetoed": len(property.vetoed_by) > 0,
                }
                for property in properties
            ],
            "request": request,
        },
    )

    return response


@app.post("/create/property/")
async def any_view(
    property: SVProperty = Depends(SVProperty.as_form),
    session: Session = Depends(get_session),
):
    logger.info(f"{property=}")

    session.add(property)
    session.commit()

    session.refresh(property)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )
