from typing import Final, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
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
)
from utils import logger

router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")


@router.get("/", response_class=HTMLResponse)
async def list_properties(
    *,
    session: Session = Depends(get_session),
    request: Request,
    object_id: Optional[str] = Cookie(default=None),
):

    properties: Final = get_properties(session)
    objects: Final = get_objects(session)
    # object_id = request.query_params.get("object_id")

    logger.info(f"### {object_id=}")

    response = templates.TemplateResponse(  # type: ignore
        "properties.html",
        {
            "properties": [
                property for property in properties if property.object_id is None
            ],
            "objects": objects,
            "object_id": object_id,
            "request": request,
        },
    )

    return response


@router.post("/create/object/")
async def route_create_object(
    *,
    session: Session = Depends(get_session),
    obj: SVObject = Depends(SVObject.as_form),
    response: Response,
):
    logger.debug(f"### {obj=}")

    object_id = obj.id
    response.set_cookie(key="object_id", value=str(object_id))

    create_object(session, obj)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/create/property/")
async def route_create_property(
    session: Session = Depends(get_session),
    property: SVProperty = Depends(SVProperty.as_form),
):
    logger.debug(f"### {property=}")
    create_property(session, property)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/veto/property/{name}")
@router.get("/user/{user}/veto/object/{obj}/property/{name}")
async def route_veto_object_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    obj: Optional[str] = None,
    name: str,
):
    veto_object_property(session, user, name, obj)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/unveto/property/{name}")
@router.get("/user/{user}/unveto/object/{obj}/property/{name}")
async def route_unveto_object_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    obj: Optional[str] = None,
    name: str,
):
    veto_object_property(session, user, name, obj, veto=False)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
