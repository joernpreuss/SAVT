from typing import Final

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from .config import settings
from .constants import HTTP_BAD_REQUEST, HTTP_CONFLICT
from .database import get_session
from .logging_config import get_logger
from .models import Feature, Item
from .service import (
    FeatureAlreadyExistsError,
    ItemAlreadyExistsError,
    create_feature,
    create_item,
    get_features,
    get_items,
    move_feature,
    veto_item_feature,
)

logger: Final = get_logger(__name__)

router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")


def _filter_standalone_features(features):
    """Filter features to return only standalone features (item_id is None)."""
    return [feature for feature in features if feature.item_id is None]


def _render_full_page_response(
    request: Request, session: Session, item_id: str | int | None = None
):
    """Render the full features page with both items and standalone features."""
    features: Final = get_features(session)
    items: Final = get_items(session)
    standalone_features = _filter_standalone_features(features)

    return templates.TemplateResponse(
        request,
        "properties.html",
        {
            "features": standalone_features,
            "items": list(items),
            "item_id": item_id,
            "settings": settings,
        },
    )


def _render_fragment_response(request: Request, session: Session, item: str | None):
    """Render appropriate fragment based on item feature vs standalone feature."""
    features: Final = get_features(session)
    items: Final = get_items(session)

    if item:  # Item feature
        return templates.TemplateResponse(
            request,
            "fragments/objects_list.html",
            {
                "items": list(items),
                "settings": settings,
            },
        )
    else:  # Standalone feature
        standalone_features = _filter_standalone_features(features)
        return templates.TemplateResponse(
            request,
            "fragments/standalone_properties.html",
            {
                "features": standalone_features,
                "items": list(items),
                "settings": settings,
            },
        )


@router.get("/", response_class=HTMLResponse)
async def list_features(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item_id: str | None = Cookie(default=None),
):
    logger.info("Debug item_id", item_id=item_id)
    return _render_full_page_response(request, session, item_id)


@router.post("/create/item/")
async def route_create_item(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item: Item = Depends(Item.as_form),
    response: Response,
):
    logger.debug("Creating item via web form", item_name=item.name)

    item_id = item.id
    response.set_cookie(key="object_id", value=str(item_id))

    try:
        create_item(session, item)
        logger.info("Item created successfully via web form", item_name=item.name)
    except ItemAlreadyExistsError as e:
        logger.warning(
            "Item creation failed - already exists",
            item_name=item.name,
            error=str(e),
        )
        raise HTTPException(status_code=HTTP_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        logger.warning(
            "Item creation failed - validation error",
            item_name=item.name,
            error=str(e),
        )
        raise HTTPException(status_code=HTTP_BAD_REQUEST, detail=str(e)) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, item_id)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/create/feature/")
async def route_create_feature(
    *,
    session: Session = Depends(get_session),
    request: Request,
    feature: Feature = Depends(Feature.as_form),
):
    logger.debug(
        "Creating feature via web form",
        feature_name=feature.name,
        created_by=feature.created_by,
    )
    try:
        create_feature(session, feature)
        logger.info(
            "Feature created successfully via web form", feature_name=feature.name
        )
    except FeatureAlreadyExistsError as e:
        logger.warning("Feature creation failed via web form", error=str(e))
        raise HTTPException(status_code=HTTP_CONFLICT, detail=str(e)) from e
    except ValueError as e:
        logger.warning(
            "Feature creation failed - validation error",
            feature_name=feature.name,
            error=str(e),
        )
        raise HTTPException(status_code=HTTP_BAD_REQUEST, detail=str(e)) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, feature.item_id)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/veto/feature/{name}")
@router.get("/user/{user}/veto/item/{item}/feature/{name}")
@router.post("/user/{user}/veto/feature/{name}")
@router.post("/user/{user}/veto/item/{item}/feature/{name}")
async def route_veto_item_feature(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    item: str | None = None,
    name: str,
):
    logger.debug(
        "Processing veto via web form", user=user, feature_name=name, item_name=item
    )
    result = veto_item_feature(session, user, name, item, veto=True)

    if result:
        logger.info(
            "Feature vetoed successfully",
            feature_name=name,
            user=user,
            item_name=item,
        )
    else:
        logger.warning(
            "Feature veto failed - not found",
            feature_name=name,
            user=user,
            item_name=item,
        )

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        return _render_fragment_response(request, session, item)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/user/{user}/unveto/feature/{name}")
@router.get("/user/{user}/unveto/item/{item}/feature/{name}")
@router.post("/user/{user}/unveto/feature/{name}")
@router.post("/user/{user}/unveto/item/{item}/feature/{name}")
async def route_unveto_item_feature(
    *,
    session: Session = Depends(get_session),
    request: Request,
    user: str,
    item: str | None = None,
    name: str,
):
    logger.debug(
        "Processing unveto via web form", user=user, feature_name=name, item_name=item
    )
    result = veto_item_feature(session, user, name, item, veto=False)

    if result:
        logger.info(
            "Feature unvetoed successfully via web form", feature_name=name, user=user
        )
    else:
        logger.warning(
            "Feature unveto failed via web form - not found", feature_name=name
        )

    # If HTMX request, return updated fragment
    if "HX-Request" in request.headers:
        return _render_fragment_response(request, session, item)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/move/feature/{feature_name}")
async def route_move_feature(
    *,
    session: Session = Depends(get_session),
    request: Request,
    feature_name: str,
    source_item: str | None = Form(None),
    target_item: str | None = Form(None),
):
    logger.debug(
        "Moving feature via web form",
        feature_name=feature_name,
        from_item=source_item,
        to_item=target_item,
    )

    try:
        result = move_feature(session, feature_name, source_item, target_item)
        if result:
            logger.info(
                "Feature moved successfully via web form",
                feature_name=feature_name,
                from_item=source_item,
                to_item=target_item,
            )
        else:
            logger.warning(
                "Feature move failed - feature not found",
                feature_name=feature_name,
                source_item=source_item,
            )
    except FeatureAlreadyExistsError as e:
        logger.warning(
            "Feature move failed - target conflict",
            feature_name=feature_name,
            target_item=target_item,
            error=str(e),
        )
        raise HTTPException(status_code=HTTP_CONFLICT, detail=str(e)) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
