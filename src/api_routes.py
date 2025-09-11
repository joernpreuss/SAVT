from typing import Final, TypedDict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from .database import get_session
from .models import SVProperty
from .service import (
    PropertyAlreadyExistsError,
    create_property,
    get_properties,
    veto_object_property,
)

api_router: Final = APIRouter(prefix="/api")


class PropertyName(BaseModel):
    name: str


@api_router.post("/properties")
async def api_create_property(
    *, session: Session = Depends(get_session), prop_name: PropertyName
):
    try:
        prop = create_property(session, SVProperty(name=prop_name.name))
        return {"created": prop.model_dump()}
    except PropertyAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@api_router.post("/users/{user}/properties")
async def api_user_create_property(
    *, session: Session = Depends(get_session), user: str, prop_name: PropertyName
):
    try:
        prop = create_property(
            session, SVProperty(name=prop_name.name, created_by=user)
        )
        return {"created": prop.model_dump()}
    except PropertyAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@api_router.post("/users/{user}/properties/{name}/veto")
async def api_user_veto_property(
    *, session: Session = Depends(get_session), user: str, name: str
):
    prop = veto_object_property(session, user, name, veto=True)

    if prop:
        return {"vetoed": prop.model_dump()}
    else:
        raise HTTPException(status_code=404, detail=f'Property "{name}" not found')


@api_router.post("/users/{user}/properties/{name}/unveto")
async def api_user_unveto_property(
    *, session: Session = Depends(get_session), user: str, name: str
):
    prop = veto_object_property(session, user, name, veto=False)

    if prop:
        return {"unvetoed": prop.model_dump()}
    else:
        raise HTTPException(status_code=404, detail=f'Property "{name}" not found')


@api_router.get("/properties")
async def api_list_properties(
    *,
    session: Session = Depends(get_session),
):
    properties = get_properties(session)

    # Define TypedDict for property structure
    class PropertyDict(TypedDict):
        name: str
        vetoed: bool

    # Sort by vetoed flag then by name for stable order
    return {
        "properties": sorted(
            [
                PropertyDict(
                    name=prop.name,
                    vetoed=len(prop.vetoed_by) > 0,
                )
                for prop in properties
            ],
            key=lambda x: (x["vetoed"], x["name"].lower()),
        )
    }
