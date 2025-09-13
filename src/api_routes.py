from typing import Final, TypedDict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from .constants import HTTP_CONFLICT, HTTP_NOT_FOUND
from .database import get_session
from .models import Feature
from .service import (
    FeatureAlreadyExistsError,
    create_feature,
    get_features,
    veto_item_feature,
)

api_router: Final = APIRouter(prefix="/api")


class FeatureName(BaseModel):
    name: str


@api_router.post("/properties")
async def api_create_feature(
    *, session: Session = Depends(get_session), feature_name: FeatureName
):
    try:
        feature = create_feature(session, Feature(name=feature_name.name))
        return {"created": feature.model_dump()}
    except FeatureAlreadyExistsError as e:
        raise HTTPException(status_code=HTTP_CONFLICT, detail=str(e)) from e


@api_router.post("/users/{user}/properties")
async def api_user_create_feature(
    *, session: Session = Depends(get_session), user: str, feature_name: FeatureName
):
    try:
        feature = create_feature(
            session, Feature(name=feature_name.name, created_by=user)
        )
        return {"created": feature.model_dump()}
    except FeatureAlreadyExistsError as e:
        raise HTTPException(status_code=HTTP_CONFLICT, detail=str(e)) from e


@api_router.post("/users/{user}/properties/{name}/veto")
async def api_user_veto_feature(
    *, session: Session = Depends(get_session), user: str, name: str
):
    feature = veto_item_feature(session, user, name, veto=True)

    if feature:
        return {"vetoed": feature.model_dump()}
    else:
        raise HTTPException(
            status_code=HTTP_NOT_FOUND, detail=f'Feature "{name}" not found'
        )


@api_router.post("/users/{user}/properties/{name}/unveto")
async def api_user_unveto_feature(
    *, session: Session = Depends(get_session), user: str, name: str
):
    feature = veto_item_feature(session, user, name, veto=False)

    if feature:
        return {"unvetoed": feature.model_dump()}
    else:
        raise HTTPException(
            status_code=HTTP_NOT_FOUND, detail=f'Feature "{name}" not found'
        )


@api_router.get("/properties")
async def api_list_features(
    *,
    session: Session = Depends(get_session),
):
    features = get_features(session)

    # Define TypedDict for feature structure
    class FeatureDict(TypedDict):
        name: str
        vetoed: bool

    # Sort by vetoed flag then by name for stable order
    return {
        "properties": sorted(
            [
                FeatureDict(
                    name=feature.name,
                    vetoed=len(feature.vetoed_by) > 0,
                )
                for feature in features
            ],
            key=lambda x: (x["vetoed"], x["name"].lower()),
        )
    }
