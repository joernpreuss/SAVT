from typing import Final

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
    object_id: str | None = Cookie(default=None),
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
    request: Request,
    obj: SVObject = Depends(SVObject.as_form),
    response: Response,
):
    logger.debug(f"### {obj=}")

    object_id = obj.id
    response.set_cookie(key="object_id", value=str(object_id))

    create_object(session, obj)

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        return templates.TemplateResponse(
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

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/create/property/")
async def route_create_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    property: SVProperty = Depends(SVProperty.as_form),
):
    logger.debug(f"### {property=}")
    create_property(session, property)

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        return templates.TemplateResponse(
            "properties.html",
            {
                "properties": [prop for prop in properties if prop.object_id is None],
                "objects": objects,
                "object_id": property.object_id,
                "request": request,
            },
        )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/veto/property/{name}")
@router.get("/user/{user}/veto/object/{obj}/property/{name}")
async def route_veto_object_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    obj: str | None = None,
    name: str,
):
    veto_object_property(session, user, name, obj)

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        if obj:  # Object property veto
            return templates.TemplateResponse(
                "fragments/objects_list.html",
                {
                    "objects": objects,
                    "request": request,
                },
            )
        else:  # Standalone property veto
            return templates.TemplateResponse(
                "fragments/standalone_properties.html",
                {
                    "properties": [
                        property
                        for property in properties
                        if property.object_id is None
                    ],
                    "request": request,
                },
            )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/unveto/property/{name}")
@router.get("/user/{user}/unveto/object/{obj}/property/{name}")
async def route_unveto_object_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    obj: str | None = None,
    name: str,
):
    veto_object_property(session, user, name, obj, veto=False)

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        if obj:  # Object property unveto
            return templates.TemplateResponse(
                "fragments/objects_list.html",
                {
                    "objects": objects,
                    "request": request,
                },
            )
        else:  # Standalone property unveto
            return templates.TemplateResponse(
                "fragments/standalone_properties.html",
                {
                    "properties": [
                        property
                        for property in properties
                        if property.object_id is None
                    ],
                    "request": request,
                },
            )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
