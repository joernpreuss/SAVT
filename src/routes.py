from typing import Final

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import select  # type: ignore
from sqlmodel import Session

from database import get_session
from models import SVProperty
from service import veto
from utils import logger

templates = Jinja2Templates(directory="templates/")

router: Final = APIRouter()


@router.get("/api/create/property/{name}")
async def api_create_property_anonymously(
    *,
    session: Session = Depends(get_session),
    name: str,
):
    property = SVProperty(name=name)
    session.add(property)
    session.commit()
    return {"created": {"name": name}}


@router.get("/api/user/{user}/create/property/{name}")
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


@router.get("/api/user/{user}/veto/property/{name}")
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


@router.get("/user/{user}/veto/property/{name}")
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


@router.get("/api/list/properties")
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


@router.get("/", response_class=HTMLResponse)
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


@router.post("/create/property/")
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
