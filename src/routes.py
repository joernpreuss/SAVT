from typing import Final

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from database import get_session
from models import SVObject, SVProperty
from service import (
    create_object,
    create_property,
    get_objects,
    get_properties,
    veto_object_property,
    veto_property_without_object,
)
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
    objects: Final = get_objects(session)

    response = templates.TemplateResponse(  # type: ignore
        "properties.html",
        {
            "properties": [
                property for property in properties if property.object_id is None
            ],
            "objects": objects,
            "request": request,
        },
    )

    return response


@router.post("/create/object/")
async def route_create_object(
    session: Session = Depends(get_session),
    object: SVObject = Depends(SVObject.as_form),
):
    logger.info(f"### {object=}")

    create_object(session, object)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/create/property/")
async def route_create_property(
    session: Session = Depends(get_session),
    property: SVProperty = Depends(SVProperty.as_form),
):
    print(f"### {property=}")

    create_property(session, property)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# old
@router.get("/user/{user}/veto/property/{name}")
async def route_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    veto_property_without_object(session, user, name)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


# new
@router.get("/user/{user}/veto/object/{obj}/property/{name}")
async def route_veto_object_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    obj: str,
    name: str,
):
    veto_object_property(session, user, obj, name)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )
