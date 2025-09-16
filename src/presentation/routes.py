from typing import Final

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Form,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from ..application.feature_service import (
    create_feature,
    delete_feature,
    get_features,
    veto_feature_by_id,
    veto_item_feature,
)
from ..application.item_operations_service import merge_items, move_feature, split_item
from ..application.item_service import (
    create_item,
    delete_item,
    get_item,
    get_items,
)
from ..config import settings
from ..domain.exceptions import DomainError
from ..infrastructure.database.database import get_session
from ..infrastructure.database.models import Feature, Item
from ..logging_config import get_logger
from ..utils import truncate_name
from .error_handlers import handle_domain_error, handle_validation_error

logger: Final = get_logger(__name__)

router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")


# Add custom filter for name truncation
def truncate_name_filter(name: str, max_length: int = 30) -> str:
    """Jinja2 filter wrapper for truncate_name utility function."""
    return truncate_name(name, max_length)


templates.env.filters["truncate_name"] = truncate_name_filter


def _filter_standalone_features(features):
    """Filter features to return only standalone features (item_id is None)."""
    return [feature for feature in features if feature.item_id is None]


def _get_next_default_item_name(session: Session) -> str:
    """Get the next available {object_name}-N name."""
    counter = 1
    base_name = settings.object_name_singular.title()
    while True:
        candidate_name = f"{base_name}-{counter}"
        if get_item(session, candidate_name) is None:
            return candidate_name
        counter += 1


def _render_full_page_response(
    request: Request,
    session: Session,
    item_id: str | int | None = None,
    message: str | None = None,
):
    """Render the full features page with both items and standalone features."""
    features: Final = get_features(session)
    items: Final = get_items(session)
    standalone_features = _filter_standalone_features(features)

    # Get the next available default name for the item name field
    next_default_name = _get_next_default_item_name(session)

    return templates.TemplateResponse(
        request,
        "properties.html",
        {
            "features": standalone_features,
            "items": list(items),
            "item_id": item_id,
            "settings": settings,
            "message": message,
            "item_name": next_default_name,  # Pre-populate the item name field only
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
    # Generate default name if empty
    if not item.name or item.name.strip() == "":
        # Find the next available {object_name}-N name
        base_name = settings.object_name_singular.title()
        counter = 1
        while True:
            candidate_name = f"{base_name}-{counter}"
            if get_item(session, candidate_name) is None:
                item.name = candidate_name
                break
            counter += 1

    logger.debug("Creating item via web form", item_name=item.name)

    item_id = item.id
    response.set_cookie(key="object_id", value=str(item_id))

    try:
        create_item(session, item)
        logger.info("Item created successfully via web form", item_name=item.name)
    except DomainError as e:
        logger.warning(
            "Item creation failed - domain error",
            item_name=item.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise handle_domain_error(e) from e
    except ValueError as e:
        logger.warning(
            "Item creation failed - validation error",
            item_name=item.name,
            error=str(e),
        )
        raise handle_validation_error(e) from e

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
        created_feature, message = create_feature(session, feature)
        logger.info(
            "Feature created successfully via web form",
            feature_name=created_feature.name,
        )
    except DomainError as e:
        logger.warning(
            "Feature creation failed - domain error",
            feature_name=feature.name,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise handle_domain_error(e) from e
    except ValueError as e:
        logger.warning(
            "Feature creation failed - validation error",
            feature_name=feature.name,
            error=str(e),
        )
        raise handle_validation_error(e) from e

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(
            request, session, created_feature.item_id, message
        )

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
    feature_id: int | None = Query(None),
):
    logger.debug(
        "Processing veto via web form",
        user=user,
        feature_name=name,
        item_name=item,
        feature_id=feature_id,
    )

    # Use feature_id if provided, otherwise fallback to name-based lookup
    if feature_id is not None:
        result = veto_feature_by_id(session, user, feature_id, veto=True)
    else:
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
    feature_id: int | None = Query(None),
):
    logger.debug(
        "Processing unveto via web form",
        user=user,
        feature_name=name,
        item_name=item,
        feature_id=feature_id,
    )

    # Use feature_id if provided, otherwise fallback to name-based lookup
    if feature_id is not None:
        result = veto_feature_by_id(session, user, feature_id, veto=False)
    else:
        result = veto_item_feature(session, user, name, item, veto=False)

    if result:
        logger.info(
            "Feature unvetoed successfully via web form",
            feature_name=name,
            user=user,
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

    result, message = move_feature(session, feature_name, source_item, target_item)
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

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/merge/item")
async def route_merge_items(
    *,
    session: Session = Depends(get_session),
    request: Request,
    source_item: str = Form(...),
    target_item: str = Form(...),
):
    logger.debug(
        "Merging items via web form",
        source_item=source_item,
        target_item=target_item,
    )

    result, message = merge_items(session, source_item, target_item)
    if result:
        logger.info(
            "Items merged successfully via web form",
            source_item=source_item,
            target_item=target_item,
        )
    else:
        logger.warning(
            "Item merge failed",
            source_item=source_item,
            target_item=target_item,
        )

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/split/item/{item_name}")
async def route_split_item(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item_name: str,
):
    logger.debug("Splitting item via web form", item_name=item_name)

    new_items, message = split_item(session, item_name)
    if new_items:
        logger.info(
            "Item split successfully via web form",
            item_name=item_name,
            new_items_count=len(new_items),
        )
    else:
        logger.warning("Item split failed", item_name=item_name)

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/delete/item/{item_name}")
@router.post("/delete/item/{item_name}")
async def route_delete_item(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item_name: str,
):
    logger.debug("Deleting item via web form", item_name=item_name)

    result = delete_item(session, item_name)
    if result:
        logger.info("Item deleted successfully via web form", item_name=item_name)
        message = f"{settings.object_name_singular.title()} '{item_name}' deleted"
    else:
        logger.warning("Item deletion failed", item_name=item_name)
        message = f"{settings.object_name_singular.title()} '{item_name}' not found"

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/delete/feature/{feature_id}")
@router.post("/delete/feature/{feature_id}")
async def route_delete_feature(
    *,
    session: Session = Depends(get_session),
    request: Request,
    feature_id: int,
):
    logger.debug("Deleting feature via web form", feature_id=feature_id)

    result = delete_feature(session, feature_id)
    if result:
        logger.info("Feature deleted successfully via web form", feature_id=feature_id)
        message = f"{settings.property_name_singular.title()} deleted successfully"
    else:
        logger.warning("Feature deletion failed", feature_id=feature_id)
        message = f"{settings.property_name_singular.title()} not found"

    # If HTMX request, return full page
    if "HX-Request" in request.headers:
        return _render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
