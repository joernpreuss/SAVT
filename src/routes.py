from typing import Final

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from database import get_session
from models import SVProperty
from service import create_property, veto_property
from utils import logger

router: Final = APIRouter()


@router.post("/create/property/")
async def any_view(
    property: SVProperty = Depends(SVProperty.as_form),
    session: Session = Depends(get_session),
):
    logger.info(f"{property=}")

    create_property(session, property)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/user/{user}/veto/property/{name}")
async def user_veto_property(
    *,
    session: Session = Depends(get_session),
    user: str,
    name: str,
):
    veto_property(session, user, name)

    return RedirectResponse(
        url="/",
        status_code=status.HTTP_303_SEE_OTHER,
    )
