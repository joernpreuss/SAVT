from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from ..application.feature_service import (
    create_feature,
    get_features,
    veto_item_feature,
)
from ..infrastructure.database.database import get_session
from ..infrastructure.database.models import Feature

api_router: Final = APIRouter(
    prefix="/api/v1",
    tags=["features"],
    responses={
        400: {"description": "Bad Request - Invalid input data"},
        404: {"description": "Not Found - Resource does not exist"},
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
        409: {"description": "Feature with this name already exists"},
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
