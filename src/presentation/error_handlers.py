"""Centralized error handling for the presentation layer."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..domain.exceptions import (
    DomainError,
    FeatureAlreadyExistsError,
    ItemAlreadyExistsError,
    ValidationError,
)

templates = Jinja2Templates(directory="templates/")


class ErrorFormatter:
    """Formats errors for consistent user experience."""

    @staticmethod
    def format_user_friendly_message(
        error: Exception, context: dict[str, Any] | None = None
    ) -> str:
        """Convert technical errors to user-friendly messages."""
        context = context or {}

        if isinstance(error, ItemAlreadyExistsError):
            return (
                f"A {settings.object_name_singular} with that name already exists. "
                "Please choose a different name."
            )

        elif isinstance(error, FeatureAlreadyExistsError):
            return (
                f"That {settings.property_name_singular} already exists. "
                "Please choose a different name."
            )

        elif isinstance(error, ValidationError):
            error_msg = str(error)
            # Make validation errors more user-friendly
            if "name cannot be empty" in error_msg.lower():
                obj_type = (
                    settings.object_name_singular
                    if "item" in error_msg.lower()
                    else settings.property_name_singular
                )
                return f"Please enter a name for the {obj_type}."
            elif "too long" in error_msg.lower():
                return "The name is too long. Please use a shorter name."
            elif "amount" in error_msg.lower():
                return (
                    f"Please enter a valid amount (1-3) for the "
                    f"{settings.property_name_singular}."
                )
            return error_msg

        elif isinstance(error, ValueError):
            # Generic validation errors
            error_msg = str(error)
            if "name cannot be empty" in error_msg.lower():
                return "Please enter a name."
            elif "amount" in error_msg.lower():
                return "Please enter a valid amount (1-3)."
            return "Please check your input and try again."

        else:
            # Fallback for unexpected errors
            return "Something went wrong. Please try again."


def handle_domain_error(error: DomainError) -> HTTPException:
    """Convert domain errors to appropriate HTTP responses."""
    user_message = ErrorFormatter.format_user_friendly_message(error)

    if isinstance(error, ItemAlreadyExistsError | FeatureAlreadyExistsError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=user_message)
    elif isinstance(error, ValidationError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=user_message
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


def handle_validation_error(error: ValueError) -> HTTPException:
    """Convert validation errors to user-friendly HTTP responses."""
    user_message = ErrorFormatter.format_user_friendly_message(error)
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=user_message)


def render_error_response(
    request: Request, error_message: str, status_code: int = 400
) -> HTMLResponse:
    """Render error response for HTML requests."""
    from .routes import get_session, render_full_page_response

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
