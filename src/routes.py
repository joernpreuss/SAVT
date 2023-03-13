from typing import Final

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from database import get_session
from models import SVProperty
from service import create_property, get_properties, veto_property
from utils import logger

router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")


@router.get("/", response_class=HTMLResponse)
async def list_properties(
    *,
    session: Session = Depends(get_session),
    request: Request,
):

    properties: Final = get_properties(session)

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

    create_property(session, property)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/user/{user}/veto/property/{name}")
async def user_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    veto_property(session, user, name)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )
