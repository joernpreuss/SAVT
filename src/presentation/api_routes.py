from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..application.feature_service import (
    create_feature,
    get_features,
    veto_item_feature,
)
from ..application.item_service import (
    ItemAlreadyExistsError,
    create_item,
    delete_item,
    get_item,
    get_items,
    restore_item,
)
from ..infrastructure.database.database import get_session
from ..infrastructure.database.models import Feature, Item

api_router: Final = APIRouter(
    prefix="/api/v1",
    tags=["features", "items"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Not Found - Resource does not exist"},
        409: {"description": "Conflict - Resource already exists"},
        422: {"description": "Validation Error - Request body validation failed"},
    },
)


# Request Models
class FeatureName(BaseModel):
    """Request model for creating a new feature/property."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the feature/property",
        examples=["Pepperoni", "Extra Cheese", "Thin Crust"],
    )


class ItemCreate(BaseModel):
    """Request model for creating a new item."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the decision item",
        examples=["Margherita Pizza", "Company Retreat Location", "Product Roadmap Q1"],
    )
    kind: str | None = Field(
        None,
        max_length=50,
        description="Optional item classification",
        examples=["vegetarian", "urgent", "quarterly"],
    )


# Response Models
class FeatureResponse(BaseModel):
    """Detailed feature information returned by the API."""

    id: int = Field(description="Unique feature identifier")
    name: str = Field(description="Feature name")
    amount: int = Field(description="Feature amount/quantity")
    item_id: int | None = Field(
        description="Associated item ID (null for standalone features)"
    )
    vetoed_by: list[str] = Field(description="List of users who vetoed this feature")
    created_by: str | None = Field(description="User who created this feature")


class FeatureCreateResponse(BaseModel):
    """Response model for feature creation."""

    created: FeatureResponse = Field(description="The newly created feature")
    message: str = Field(description="Success message")


class FeatureActionResponse(BaseModel):
    """Response model for veto/unveto actions."""

    vetoed: FeatureResponse | None = Field(
        None, description="Feature after veto action"
    )
    unvetoed: FeatureResponse | None = Field(
        None, description="Feature after unveto action"
    )


class FeatureListItem(BaseModel):
    """Simplified feature information for list responses."""

    name: str = Field(description="Feature name")
    vetoed: bool = Field(description="Whether this feature has any vetos")


class FeatureListResponse(BaseModel):
    """Response model for listing features."""

    properties: list[FeatureListItem] = Field(
        description="List of all features, sorted by veto status then name"
    )


class ItemResponse(BaseModel):
    """Detailed item information returned by the API."""

    id: int = Field(description="Unique item identifier")
    name: str = Field(description="Item name")
    kind: str | None = Field(description="Item classification (optional)")
    created_by: str | None = Field(description="User who created this item")
    features: list[FeatureResponse] = Field(
        description="Associated features/properties"
    )


class ItemCreateResponse(BaseModel):
    """Response model for item creation."""

    created: ItemResponse = Field(description="The newly created item")
    message: str = Field(description="Success message")


class ItemListItem(BaseModel):
    """Simplified item information for list responses."""

    id: int = Field(description="Unique item identifier")
    name: str = Field(description="Item name")
    kind: str | None = Field(description="Item classification (optional)")
    feature_count: int = Field(description="Number of associated features")
    vetoed_feature_count: int = Field(description="Number of vetoed features")


class ItemListResponse(BaseModel):
    """Response model for listing items."""

    items: list[ItemListItem] = Field(
        description="List of all items with feature counts"
    )


class ItemActionResponse(BaseModel):
    """Response model for item actions like delete/restore."""

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Result message")
    item_name: str = Field(description="Name of the affected item")


@api_router.post(
    "/properties",
    response_model=FeatureCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a standalone feature",
    description="""
    Create a new standalone feature/property that is not associated with any
    specific item.

    This is useful for creating a pool of potential features that can later be
    associated with decision items, or for features that apply globally across
    multiple items.

    **Example**: Creating "Vegetarian Option" that could apply to multiple food items.
    """,
    responses={
        201: {
            "description": "Feature created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "created": {
                            "id": 42,
                            "name": "Extra Cheese",
                            "amount": 1,
                            "item_id": None,
                            "vetoed_by": [],
                            "created_by": None,
                        },
                        "message": "Feature created successfully",
                    }
                }
            },
        },
    },
)
async def api_create_feature(
    *, session: Session = Depends(get_session), feature_name: FeatureName
) -> FeatureCreateResponse:
    """Create a new standalone feature/property."""
    feature, message = create_feature(session, Feature(name=feature_name.name))
    return FeatureCreateResponse(
        created=FeatureResponse(
            id=feature.id,
            name=feature.name,
            amount=feature.amount,
            item_id=feature.item_id,
            vetoed_by=feature.vetoed_by,
            created_by=feature.created_by,
        ),
        message=message or "Feature created successfully",
    )


@api_router.post(
    "/users/{user}/properties",
    response_model=FeatureCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["users"],
    summary="Create a feature as a specific user",
    description="""
    Create a new feature/property attributed to a specific user.

    This endpoint tracks who suggested the feature, enabling proper attribution
    and potentially different permissions or voting weights in future versions.

    **Use case**: User "alice" suggests "Mushrooms" for a pizza decision.
    """,
    responses={
        201: {
            "description": "Feature created successfully with user attribution",
            "content": {
                "application/json": {
                    "example": {
                        "created": {
                            "id": 43,
                            "name": "Mushrooms",
                            "amount": 1,
                            "item_id": None,
                            "vetoed_by": [],
                            "created_by": "alice",
                        },
                        "message": "Feature created successfully",
                    }
                }
            },
        }
    },
)
async def api_user_create_feature(
    *,
    session: Session = Depends(get_session),
    user: str = Path(description="Username of the person creating the feature"),
    feature_name: FeatureName,
) -> FeatureCreateResponse:
    """Create a new feature/property attributed to a specific user."""
    feature, message = create_feature(
        session, Feature(name=feature_name.name, created_by=user)
    )
    return FeatureCreateResponse(
        created=FeatureResponse(
            id=feature.id,
            name=feature.name,
            amount=feature.amount,
            item_id=feature.item_id,
            vetoed_by=feature.vetoed_by,
            created_by=feature.created_by,
        ),
        message=message or "Feature created successfully",
    )


@api_router.post(
    "/users/{user}/properties/{name}/veto",
    response_model=FeatureActionResponse,
    tags=["users"],
    summary="Veto a feature",
    description="""
    Apply a veto to a specific feature by name for a given user.

    **Veto System**: Each user can independently veto features they don't want.
    Features with any vetos are typically excluded from final decisions unless
    the vetos are later removed (unveiled).

    **Idempotent**: Calling this multiple times for the same user/feature has no
    additional effect.

    **Example**: User "bob" vetos "Anchovies" because they don't like them.
    """,
    responses={
        200: {
            "description": "Feature vetoed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "vetoed": {
                            "id": 44,
                            "name": "Anchovies",
                            "amount": 1,
                            "item_id": None,
                            "vetoed_by": ["bob"],
                            "created_by": "alice",
                        }
                    }
                }
            },
        },
        404: {"description": "Feature with the specified name not found"},
    },
)
async def api_user_veto_feature(
    *,
    session: Session = Depends(get_session),
    user: str = Path(description="Username of the person applying the veto"),
    name: str = Path(description="Exact name of the feature to veto"),
) -> FeatureActionResponse:
    """Apply a veto to a feature by name for a specific user."""
    feature = veto_item_feature(session, user, name, veto=True)

    if feature:
        return FeatureActionResponse(
            vetoed=FeatureResponse(
                id=feature.id,
                name=feature.name,
                amount=feature.amount,
                item_id=feature.item_id,
                vetoed_by=feature.vetoed_by,
                created_by=feature.created_by,
            )
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f'Feature "{name}" not found'
        )


@api_router.post(
    "/users/{user}/properties/{name}/unveto",
    response_model=FeatureActionResponse,
    tags=["users"],
    summary="Remove veto from a feature",
    description="""
    Remove a user's veto from a specific feature by name.

    **Unveto System**: Users can change their mind and remove their veto,
    potentially making a feature eligible for inclusion in the final decision.

    **Idempotent**: Calling this multiple times for the same user/feature has no
    additional effect.

    **Example**: User "bob" changes their mind and unvetos "Pineapple" after
    initially vetoing it.
    """,
    responses={
        200: {
            "description": "Veto removed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "unvetoed": {
                            "id": 45,
                            "name": "Pineapple",
                            "amount": 1,
                            "item_id": None,
                            "vetoed_by": [],
                            "created_by": "alice",
                        }
                    }
                }
            },
        },
        404: {"description": "Feature with the specified name not found"},
    },
)
async def api_user_unveto_feature(
    *,
    session: Session = Depends(get_session),
    user: str = Path(description="Username of the person removing their veto"),
    name: str = Path(description="Exact name of the feature to unveto"),
) -> FeatureActionResponse:
    """Remove a user's veto from a feature by name."""
    feature = veto_item_feature(session, user, name, veto=False)

    if feature:
        return FeatureActionResponse(
            unvetoed=FeatureResponse(
                id=feature.id,
                name=feature.name,
                amount=feature.amount,
                item_id=feature.item_id,
                vetoed_by=feature.vetoed_by,
                created_by=feature.created_by,
            )
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f'Feature "{name}" not found'
        )


@api_router.get(
    "/properties",
    response_model=FeatureListResponse,
    summary="List all features",
    description="""
    Retrieve a list of all features/properties in the system.

    **Sorting**: Results are sorted by veto status (non-vetoed first), then
    alphabetically by name. This ensures that viable options appear at the top of
    the list.

    **Response Format**: Simplified view showing only name and veto status for
    efficient listing. Use individual feature endpoints for detailed information.

    **Use case**: Display all available toppings for a pizza, highlighting which
    ones have been vetoed.
    """,
    responses={
        200: {
            "description": "List of all features with their veto status",
            "content": {
                "application/json": {
                    "example": {
                        "properties": [
                            {"name": "Cheese", "vetoed": False},
                            {"name": "Pepperoni", "vetoed": False},
                            {"name": "Anchovies", "vetoed": True},
                            {"name": "Pineapple", "vetoed": True},
                        ]
                    }
                }
            },
        }
    },
)
async def api_list_features(
    *,
    session: Session = Depends(get_session),
) -> FeatureListResponse:
    """Retrieve a list of all features/properties with their veto status."""
    features = get_features(session)

    # Sort by vetoed flag then by name for stable order
    feature_items = sorted(
        [
            FeatureListItem(
                name=feature.name,
                vetoed=len(feature.vetoed_by) > 0,
            )
            for feature in features
        ],
        key=lambda x: (x.vetoed, x.name.lower()),
    )

    return FeatureListResponse(properties=feature_items)


# Item API Endpoints


@api_router.post(
    "/items",
    response_model=ItemCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["items"],
    summary="Create a new decision item",
    description="""
    Create a new item for group decision-making.

    Items are containers for features/properties that require group decisions.
    Each item has a unique name and can optionally be classified with a 'kind'.

    **Examples**:
    - Pizza ordering: Create "Margherita Pizza" item to collect topping preferences
    - Event planning: Create "Company Retreat" item to gather location/activity options
    - Product decisions: Create "Q1 Roadmap" item for feature prioritization

    **Business Rules**:
    - Item names must be unique system-wide
    - Names cannot be empty and have a maximum length
    - Items are never deleted, only soft-deleted for data preservation
    """,
    responses={
        201: {
            "description": "Item created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "created": {
                            "id": 1,
                            "name": "Margherita Pizza",
                            "kind": "vegetarian",
                            "created_by": None,
                            "features": [],
                        },
                        "message": "Item created successfully",
                    }
                }
            },
        },
        409: {
            "description": "Item with this name already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Item with name 'Margherita Pizza' already exists"
                    }
                }
            },
        },
    },
)
async def api_create_item(
    *, session: Session = Depends(get_session), item_data: ItemCreate
) -> ItemCreateResponse:
    """Create a new decision item."""
    try:
        item = create_item(session, Item(name=item_data.name, kind=item_data.kind))
        return ItemCreateResponse(
            created=ItemResponse(
                id=item.id,
                name=item.name,
                kind=item.kind,
                created_by=item.created_by,
                features=[],
            ),
            message="Item created successfully",
        )
    except ItemAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@api_router.post(
    "/users/{user}/items",
    response_model=ItemCreateResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["items", "users"],
    summary="Create an item as a specific user",
    description="""
    Create a new decision item attributed to a specific user.

    This endpoint tracks who created the item, enabling proper attribution
    and potentially different permissions in future versions.

    **Use case**: User "alice" creates "Team Lunch Options" for group decision-making.
    """,
    responses={
        201: {
            "description": "Item created successfully with user attribution",
            "content": {
                "application/json": {
                    "example": {
                        "created": {
                            "id": 2,
                            "name": "Team Lunch Options",
                            "kind": None,
                            "created_by": "alice",
                            "features": [],
                        },
                        "message": "Item created successfully",
                    }
                }
            },
        }
    },
)
async def api_user_create_item(
    *,
    session: Session = Depends(get_session),
    user: str = Path(description="Username of the person creating the item"),
    item_data: ItemCreate,
) -> ItemCreateResponse:
    """Create a new decision item attributed to a specific user."""
    try:
        item = create_item(
            session, Item(name=item_data.name, kind=item_data.kind, created_by=user)
        )
        return ItemCreateResponse(
            created=ItemResponse(
                id=item.id,
                name=item.name,
                kind=item.kind,
                created_by=item.created_by,
                features=[],
            ),
            message="Item created successfully",
        )
    except ItemAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e


@api_router.get(
    "/items",
    response_model=ItemListResponse,
    tags=["items"],
    summary="List all items",
    description="""
    Retrieve a list of all decision items in the system.

    **Response Format**: Shows item metadata with feature counts for efficient
    overview. Use individual item endpoints for detailed feature information.

    **Feature Counts**: Includes total features and vetoed features for each item,
    helping identify items with consensus (few vetoes) vs. contested items.

    **Sorting**: Results are sorted alphabetically by name for consistent ordering.

    **Use case**: Dashboard view showing all active decisions with their progress.
    """,
    responses={
        200: {
            "description": "List of all items with feature counts",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "name": "Company Retreat",
                                "kind": "event",
                                "feature_count": 5,
                                "vetoed_feature_count": 2,
                            },
                            {
                                "id": 2,
                                "name": "Q1 Product Roadmap",
                                "kind": "planning",
                                "feature_count": 8,
                                "vetoed_feature_count": 1,
                            },
                        ]
                    }
                }
            },
        }
    },
)
async def api_list_items(
    *, session: Session = Depends(get_session)
) -> ItemListResponse:
    """Retrieve a list of all decision items with feature counts."""
    items = get_items(session)

    item_list = sorted(
        [
            ItemListItem(
                id=item.id,
                name=item.name,
                kind=item.kind,
                feature_count=len(item.features),
                vetoed_feature_count=len(
                    [f for f in item.features if len(f.vetoed_by) > 0]
                ),
            )
            for item in items
        ],
        key=lambda x: x.name.lower(),
    )

    return ItemListResponse(items=item_list)


@api_router.get(
    "/items/{item_name}",
    response_model=ItemResponse,
    tags=["items"],
    summary="Get item details",
    description="""
    Retrieve detailed information about a specific item by name.

    **Complete Data**: Returns full item information including all associated
    features with their veto status and attribution.

    **Use case**: Display full decision details for a specific item, showing
    all proposed features and their current veto status.
    """,
    responses={
        200: {
            "description": "Detailed item information",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Margherita Pizza",
                        "kind": "vegetarian",
                        "created_by": "alice",
                        "features": [
                            {
                                "id": 1,
                                "name": "Extra Cheese",
                                "amount": 1,
                                "item_id": 1,
                                "vetoed_by": [],
                                "created_by": "bob",
                            },
                            {
                                "id": 2,
                                "name": "Anchovies",
                                "amount": 1,
                                "item_id": 1,
                                "vetoed_by": ["alice", "charlie"],
                                "created_by": "bob",
                            },
                        ],
                    }
                }
            },
        },
        404: {"description": "Item with the specified name not found"},
    },
)
async def api_get_item(
    *,
    session: Session = Depends(get_session),
    item_name: str = Path(description="Exact name of the item to retrieve"),
) -> ItemResponse:
    """Retrieve detailed information about a specific item."""
    item = get_item(session, item_name)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Item "{item_name}" not found',
        )

    return ItemResponse(
        id=item.id,
        name=item.name,
        kind=item.kind,
        created_by=item.created_by,
        features=[
            FeatureResponse(
                id=feature.id,
                name=feature.name,
                amount=feature.amount,
                item_id=feature.item_id,
                vetoed_by=feature.vetoed_by,
                created_by=feature.created_by,
            )
            for feature in item.features
        ],
    )


@api_router.delete(
    "/items/{item_name}",
    response_model=ItemActionResponse,
    tags=["items"],
    summary="Soft delete an item",
    description="""
    Soft delete an item and move its features to standalone status.

    **Data Preservation**: Items are never permanently deleted. They are marked
    as deleted but remain in the database for audit purposes.

    **Feature Handling**: All features associated with the deleted item become
    standalone features (no longer tied to any item).

    **Reversible**: Deleted items can be restored using the restore endpoint.

    **Use case**: Remove a decision item that's no longer relevant while
    preserving the suggested features for potential reuse.
    """,
    responses={
        200: {
            "description": "Item soft deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Item 'Old Project' deleted successfully",
                        "item_name": "Old Project",
                    }
                }
            },
        },
        404: {"description": "Item with the specified name not found"},
    },
)
async def api_delete_item(
    *,
    session: Session = Depends(get_session),
    item_name: str = Path(description="Exact name of the item to delete"),
) -> ItemActionResponse:
    """Soft delete an item and move its features to standalone."""
    success = delete_item(session, item_name)

    if success:
        return ItemActionResponse(
            success=True,
            message=f"Item '{item_name}' deleted successfully",
            item_name=item_name,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Item "{item_name}" not found',
        )


@api_router.post(
    "/items/{item_name}/restore",
    response_model=ItemActionResponse,
    tags=["items"],
    summary="Restore a deleted item",
    description="""
    Restore a previously soft-deleted item.

    **Recovery**: Brings back a deleted item and makes it available for
    decision-making again.

    **Note**: This does NOT automatically reassociate features that were moved
    to standalone status during deletion. Features must be manually reassociated
    if desired.

    **Use case**: Undo an accidental deletion or revive a decision that becomes
    relevant again.
    """,
    responses={
        200: {
            "description": "Item restored successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Item 'Revived Project' restored successfully",
                        "item_name": "Revived Project",
                    }
                }
            },
        },
        404: {"description": "Deleted item with the specified name not found"},
    },
)
async def api_restore_item(
    *,
    session: Session = Depends(get_session),
    item_name: str = Path(description="Exact name of the item to restore"),
) -> ItemActionResponse:
    """Restore a previously deleted item."""
    success = restore_item(session, item_name)

    if success:
        return ItemActionResponse(
            success=True,
            message=f"Item '{item_name}' restored successfully",
            item_name=item_name,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Deleted item "{item_name}" not found',
        )
