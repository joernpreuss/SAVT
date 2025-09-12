from typing import Final

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from .database import get_session
from .logging_config import get_logger
from .models import SVObject, SVProperty
from .service import (
    ObjectAlreadyExistsError,
    PropertyAlreadyExistsError,
    create_object,
    create_property,
    get_objects,
    get_properties,
    veto_object_property,
)

logger = get_logger(__name__)

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

    logger.info("Debug object_id", object_id=object_id)

    # Create filtered properties list with explicit type
    standalone_properties = [prop for prop in properties if prop.object_id is None]

    response = templates.TemplateResponse(
        request,
        "properties.html",
        {
            "properties": standalone_properties,
            "objects": list(objects),
            "object_id": object_id,
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
    logger.debug("Creating object via web form", object_name=obj.name)

    object_id = obj.id
    response.set_cookie(key="object_id", value=str(object_id))

    try:
        create_object(session, obj)
        logger.info("Object created successfully via web form", object_name=obj.name)
    except ObjectAlreadyExistsError as e:
        logger.warning(
            "Object creation failed - already exists",
            object_name=obj.name,
            error=str(e),
        )
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        logger.warning(
            "Object creation failed - validation error",
            object_name=obj.name,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        # Create filtered properties list
        standalone_properties = [prop for prop in properties if prop.object_id is None]

        return templates.TemplateResponse(
            request,
            "properties.html",
            {
                "properties": standalone_properties,
                "objects": list(objects),
                "object_id": object_id,
            },
        )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/create/property/")
async def route_create_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    prop: SVProperty = Depends(SVProperty.as_form),
):
    logger.debug(
        "Creating property via web form",
        property_name=prop.name,
        created_by=prop.created_by,
    )
    try:
        create_property(session, prop)
        logger.info(
            "Property created successfully via web form", property_name=prop.name
        )
    except PropertyAlreadyExistsError as e:
        logger.warning("Property creation failed via web form", error=str(e))
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        logger.warning(
            "Property creation failed - validation error",
            property_name=prop.name,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e)) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        # Create filtered properties list
        standalone_properties = [p for p in properties if p.object_id is None]

        return templates.TemplateResponse(
            request,
            "properties.html",
            {
                "properties": standalone_properties,
                "objects": list(objects),
                "object_id": prop.object_id,
            },
        )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/veto/property/{name}")
@router.get("/user/{user}/veto/object/{obj}/property/{name}")
@router.post("/user/{user}/veto/property/{name}")
@router.post("/user/{user}/veto/object/{obj}/property/{name}")
async def route_veto_object_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    obj: str | None = None,
    name: str,
):
    logger.debug(
        "Processing veto via web form", user=user, property_name=name, object_name=obj
    )
    result = veto_object_property(session, user, name, obj, veto=True)

    if result:
        logger.info(
            "Property vetoed successfully",
            property_name=name,
            user=user,
            object_name=obj,
        )
    else:
        logger.warning(
            "Property veto failed - not found",
            property_name=name,
            user=user,
            object_name=obj,
        )

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        if obj:  # Object property veto
            return templates.TemplateResponse(
                request,
                "fragments/objects_list.html",
                {
                    "objects": list(objects),
                },
            )
        else:  # Standalone property veto
            # Create filtered properties list
            standalone_properties = [
                prop for prop in properties if prop.object_id is None
            ]
            return templates.TemplateResponse(
                request,
                "fragments/standalone_properties.html",
                {
                    "properties": standalone_properties,
                },
            )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/unveto/property/{name}")
@router.get("/user/{user}/unveto/object/{obj}/property/{name}")
@router.post("/user/{user}/unveto/property/{name}")
@router.post("/user/{user}/unveto/object/{obj}/property/{name}")
async def route_unveto_object_property(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    obj: str | None = None,
    name: str,
):
    logger.debug(
        "Processing unveto via web form", user=user, property_name=name, object_name=obj
    )
    result = veto_object_property(session, user, name, obj, veto=False)

    if result:
        logger.info(
            "Property unvetoed successfully via web form", property_name=name, user=user
        )
    else:
        logger.warning(
            "Property unveto failed via web form - not found", property_name=name
        )

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        properties: Final = get_properties(session)
        objects: Final = get_objects(session)

        if obj:  # Object property unveto
            return templates.TemplateResponse(
                request,
                "fragments/objects_list.html",
                {
                    "objects": list(objects),
                },
            )
        else:  # Standalone property unveto
            # Create filtered properties list
            standalone_properties = [
                prop for prop in properties if prop.object_id is None
            ]
            return templates.TemplateResponse(
                request,
                "fragments/standalone_properties.html",
                {
                    "properties": standalone_properties,
                },
            )

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
