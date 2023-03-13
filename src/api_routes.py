from typing import Final

from fastapi import APIRouter, Depends
from sqlmodel import Session

from database import get_session
from models import SVProperty
from service import create_property, get_properties, veto_property_without_object

api_router: Final = APIRouter()


@api_router.get("/api/create/property/{name}")
async def api_create_property_anonymously(
    *,
    session: Session = Depends(get_session),
    name: str,
):
    create_property(session, SVProperty(name=name))
    return {"created": {"name": name}}


@api_router.get("/api/user/{user}/create/property/{name}")
async def api_user_create_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    property: Final = create_property(session, SVProperty(name=name, created_by=user))

    # TODO error handling
    if property:
        return {"created": dict(property)}
    else:
        return {"error": f'property "{name}" already exists'}


@api_router.get("/api/user/{user}/veto/property/{name}")
async def api_user_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    property: Final = veto_property_without_object(session, user, name)

    if property:
        return {"vetoed": property.dict()}

    else:
        return {"error": f'property "{name}" not found'}


@api_router.get("/api/list/properties")
async def api_list_properties(
    *,
    session: Session = Depends(get_session),
):
    properties = get_properties(session)

    return {
        "properties": sorted(
            [
                {
                    "name": property.name,
                    "vetoed": len(property.vetoed_by) > 0,
                }
                for property in properties
            ],
            key=lambda x: x["vetoed"],  # sort by "vetoed"
        )
    }
