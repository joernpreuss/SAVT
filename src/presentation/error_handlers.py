"""Centralized error handling for the presentation layer."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from ..domain.exceptions import (
    DomainError,
    FeatureAlreadyExistsError,
    ItemAlreadyExistsError,
    ValidationError,
)
from .problem_details import (
    ErrorCodes,
    ProblemDetailFactory,
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


def handle_domain_error(
    error: DomainError, request: Request
) -> HTTPException | JSONResponse:
    """Convert domain errors to appropriate HTTP responses."""
    user_message = ErrorFormatter.format_user_friendly_message(error)

    # Check if this is an API request
    if request.url.path.startswith("/api/"):
        # Return RFC 7807 Problem Details for API requests
        if isinstance(error, ItemAlreadyExistsError):
            problem = ProblemDetailFactory.resource_already_exists(
                resource_type="item",
                detail=user_message,
                instance=str(request.url.path),
                conflicting_field="name",
            )
        elif isinstance(error, FeatureAlreadyExistsError):
            problem = ProblemDetailFactory.resource_already_exists(
                resource_type="feature",
                detail=user_message,
                instance=str(request.url.path),
                conflicting_field="name",
            )
        elif isinstance(error, ValidationError):
            field_errors = _extract_field_errors(error)
            problem = ProblemDetailFactory.validation_failed(
                detail=user_message,
                instance=str(request.url.path),
                field_errors=field_errors,
            )
        else:
            problem = ProblemDetailFactory.internal_server_error(
                detail="An unexpected error occurred. Please try again.",
                instance=str(request.url.path),
            )

        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(exclude_none=True),
        )
    else:
        # Return traditional HTTPException for HTML requests
        if isinstance(error, ItemAlreadyExistsError | FeatureAlreadyExistsError):
            return HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail=user_message
            )
        elif isinstance(error, ValidationError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=user_message
            )
        else:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred. Please try again.",
            )


def handle_validation_error(
    error: ValueError, request: Request
) -> HTTPException | JSONResponse:
    """Convert validation errors to user-friendly HTTP responses."""
    user_message = ErrorFormatter.format_user_friendly_message(error)

    # Check if this is an API request
    if request.url.path.startswith("/api/"):
        field_errors = _extract_field_errors_from_value_error(error)
        problem = ProblemDetailFactory.validation_failed(
            detail=user_message,
            instance=str(request.url.path),
            field_errors=field_errors,
        )
        return JSONResponse(
            status_code=problem.status,
            content=problem.model_dump(exclude_none=True),
        )
    else:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=user_message
        )


def _extract_field_errors(error: ValidationError) -> list[dict[str, str]]:
    """Extract field-specific errors from ValidationError."""
    errors = []
    error_msg = str(error).lower()

    if "name" in error_msg:
        if "empty" in error_msg:
            errors.append(
                {
                    "field": "name",
                    "code": ErrorCodes.FIELD_REQUIRED,
                    "message": "Name is required",
                }
            )
        elif "too long" in error_msg or "longer" in error_msg:
            errors.append(
                {
                    "field": "name",
                    "code": ErrorCodes.FIELD_TOO_LONG,
                    "message": "Name is too long",
                }
            )
        elif "control characters" in error_msg:
            errors.append(
                {
                    "field": "name",
                    "code": ErrorCodes.FIELD_INVALID_FORMAT,
                    "message": "Name contains invalid characters",
                }
            )

    if "amount" in error_msg:
        errors.append(
            {
                "field": "amount",
                "code": ErrorCodes.FIELD_INVALID_VALUE,
                "message": "Amount must be between 1 and 3",
            }
        )

    return errors


def _extract_field_errors_from_value_error(error: ValueError) -> list[dict[str, str]]:
    """Extract field-specific errors from ValueError."""
    errors = []
    error_msg = str(error).lower()

    if "name" in error_msg:
        if "empty" in error_msg:
            errors.append(
                {
                    "field": "name",
                    "code": ErrorCodes.FIELD_REQUIRED,
                    "message": "Name is required",
                }
            )
        elif "too long" in error_msg:
            errors.append(
                {
                    "field": "name",
                    "code": ErrorCodes.FIELD_TOO_LONG,
                    "message": "Name is too long",
                }
            )

    if "amount" in error_msg:
        errors.append(
            {
                "field": "amount",
                "code": ErrorCodes.FIELD_INVALID_VALUE,
                "message": "Amount must be between 1 and 3",
            }
        )

    return errors


def render_error_response(
    request: Request, error_message: str, status_code: int = 400
) -> HTMLResponse:
    """Render error response for HTML requests."""

    # For HTML responses, show the error message on the main page
    try:
        from .routes import get_session, render_full_page_response

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
