import asyncio
from typing import Final

from fastapi import APIRouter, Cookie, Depends, Form, Query, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session

from ..application.feature_service import (
    create_feature,
    delete_feature,
    get_features,
    get_features_async,
    restore_feature,
    veto_feature_by_id,
    veto_item_feature,
)
from ..application.item_operations_service import merge_items, move_feature, split_item
from ..application.item_service import (
    create_item,
    delete_item,
    get_item,
    get_items,
    get_items_async,
    restore_item,
)
from ..config import settings
from ..domain.exceptions import DomainError
from ..infrastructure.database.database import get_async_engine, get_session
from ..infrastructure.database.database import get_async_session as get_async_session
from ..infrastructure.database.models import Feature, Item
from ..logging_config import get_logger
from ..request_utils import is_htmx_request
from ..utils import truncate_name
from .error_handlers import handle_domain_error, handle_validation_error

logger: Final = get_logger(__name__)

router: Final = APIRouter()
templates: Final = Jinja2Templates(directory="templates/")


# Add custom filter for name truncation
def _truncate_name_filter(name: str, max_length: int = 30) -> str:
    """Jinja2 filter wrapper for truncate_name utility function."""
    return truncate_name(name, max_length)


templates.env.filters["truncate_name"] = _truncate_name_filter


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


def _get_next_default_item_name_simple() -> str:
    """Get a default item name without database lookup for faster async rendering."""
    import time

    base_name = settings.object_name_singular.title()
    timestamp = int(time.time() * 1000) % 100000  # Last 5 digits for uniqueness
    return f"{base_name}-{timestamp}"


def render_full_page_response(
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


async def render_full_page_response_async(
    request: Request,
    session: AsyncSession,
    item_id: str | int | None = None,
    message: str | None = None,
):
    """Render the full features page with concurrent database operations for better
    performance."""

    async def get_features_task():
        async with AsyncSession(get_async_engine()) as task_session:
            return await get_features_async(task_session)

    async def get_items_task():
        async with AsyncSession(get_async_engine()) as task_session:
            return await get_items_async(task_session)

    async with asyncio.TaskGroup() as tg:
        features_task = tg.create_task(get_features_task())
        items_task = tg.create_task(get_items_task())

    features = features_task.result()
    items = items_task.result()
    standalone_features = _filter_standalone_features(features)

    # Get the next available default name for the item name field
    # Using simple version to avoid additional database query for better performance
    next_default_name = _get_next_default_item_name_simple()

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
def list_features(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item_id: str | None = Cookie(default=None),
):
    logger.info("Debug item_id", item_id=item_id)
    return render_full_page_response(request, session, item_id)


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
        return handle_domain_error(e, request)
    except ValueError as e:
        logger.warning(
            "Item creation failed - validation error",
            item_name=item.name,
            error=str(e),
        )
        return handle_validation_error(e, request)

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(request, session, item_id)

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
        return handle_domain_error(e, request)
    except ValueError as e:
        logger.warning(
            "Feature creation failed - validation error",
            feature_name=feature.name,
            error=str(e),
        )
        return handle_validation_error(e, request)

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(
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
    if is_htmx_request(request):
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
    if is_htmx_request(request):
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
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

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
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

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
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

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
        undo_link = (
            f"<a href='/undo/item/{item_name}' hx-post='/undo/item/{item_name}' "
            f"hx-target='body' hx-swap='outerHTML' class='undo-link'>Undo</a>"
        )
        obj_name = settings.object_name_singular.title()
        message = f"{obj_name} '{item_name}' deleted. {undo_link}"
    else:
        logger.warning("Item deletion failed", item_name=item_name)
        message = f"{settings.object_name_singular.title()} '{item_name}' not found"

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

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
        undo_url = f"/undo/feature/{feature_id}"
        undo_link = (
            f"<a href='{undo_url}' hx-post='{undo_url}' "
            f"hx-target='body' hx-swap='outerHTML' class='undo-link'>Undo</a>"
        )
        message = f"{settings.property_name_singular.title()} deleted. {undo_link}"
    else:
        logger.warning("Feature deletion failed", feature_id=feature_id)
        message = f"{settings.property_name_singular.title()} not found"

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/undo/item/{item_name}")
async def route_undo_item_deletion(
    *,
    session: Session = Depends(get_session),
    request: Request,
    item_name: str,
):
    logger.debug("Undoing item deletion via web form", item_name=item_name)

    success = restore_item(session, item_name)
    if success:
        logger.info("Item restored successfully", item_name=item_name)
        message = f"Item '{item_name}' restored successfully"
    else:
        logger.warning("Item restore failed", item_name=item_name)
        message = f"Failed to restore item '{item_name}'"

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/undo/feature/{feature_id}")
async def route_undo_feature_deletion(
    *,
    session: Session = Depends(get_session),
    request: Request,
    feature_id: int,
):
    logger.debug("Undoing feature deletion via web form", feature_id=feature_id)

    success = restore_feature(session, feature_id)
    if success:
        logger.info("Feature restored successfully", feature_id=feature_id)
        message = "Feature restored successfully"
    else:
        logger.warning("Feature restore failed", feature_id=feature_id)
        message = "Failed to restore feature"

    # If HTMX request, return full page
    if is_htmx_request(request):
        return render_full_page_response(request, session, message=message)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


def render_error_response(
    request: Request, error_message: str, status_code: int = 400
) -> HTMLResponse:
    """Render error response for HTML requests."""
    # For HTML responses, show the error message on the main page
    try:
        session = next(get_session())
        response = render_full_page_response(request, session, message=error_message)
        response.status_code = status_code
        return response
    except Exception:
        # Fallback if main page rendering fails
        return templates.TemplateResponse(
            request,
            "error.html",
            {"error_message": error_message, "settings": settings},
            status_code=status_code,
        )
