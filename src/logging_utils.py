import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Request


def log_user_action(
    action: str, user: str, logger_name: str = "user_actions", **kwargs: Any
) -> None:
    """Log user actions with consistent structure.

    Args:
        action: The action being performed (e.g., 'create_property', 'veto_property')
        user: Username performing the action
        logger_name: Name of the logger to use
        **kwargs: Additional context data
    """
    logger = logging.getLogger(logger_name)

    log_data = {
        "action": action,
        "user": user,
        "timestamp": datetime.now(UTC).isoformat(),
        **kwargs,
    }

    logger.info(f"User action: {action} by {user}", extra=log_data)


def log_api_request(
    request: Request,
    response_status: int,
    process_time_ms: float | None = None,
    logger_name: str = "api",
) -> None:
    """Log API requests with consistent format.

    Args:
        request: FastAPI request object
        response_status: HTTP response status code
        process_time_ms: Request processing time in milliseconds
        logger_name: Name of the logger to use
    """
    logger = logging.getLogger(logger_name)

    log_data = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response_status,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "Unknown")[:100],
    }

    if process_time_ms is not None:
        log_data["process_time_ms"] = str(round(process_time_ms, 2))

    # Different log levels based on status code
    if response_status >= 500:
        log_level = logging.ERROR
    elif response_status >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO

    message = f"{request.method} {request.url.path} - {response_status}"
    if process_time_ms is not None:
        message += f" ({process_time_ms:.1f}ms)"

    logger.log(log_level, message, extra=log_data)


def log_database_operation(
    operation: str,
    table: str,
    success: bool = True,
    logger_name: str = "database",
    **kwargs: Any,
) -> None:
    """Log database operations.

    Args:
        operation: Database operation (create, update, delete, select)
        table: Table name being operated on
        success: Whether the operation was successful
        logger_name: Name of the logger to use
        **kwargs: Additional context data
    """
    logger = logging.getLogger(logger_name)

    log_data = {"operation": operation, "table": table, "success": success, **kwargs}

    level = logging.INFO if success else logging.ERROR
    status = "succeeded" if success else "failed"

    logger.log(level, f"Database {operation} on {table} {status}", extra=log_data)


def log_system_info(hostname: str, ip_address: str, debug_mode: bool) -> None:
    """Log system startup information.

    Args:
        hostname: Server hostname
        ip_address: Server IP address
        debug_mode: Whether debug mode is enabled
    """
    logger = logging.getLogger("system")

    logger.info(
        "Application startup",
        extra={
            "hostname": hostname,
            "ip_address": ip_address,
            "debug_mode": debug_mode,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


def log_validation_error(
    field: str, value: Any, error_message: str, logger_name: str = "validation"
) -> None:
    """Log validation errors with context.

    Args:
        field: Field name that failed validation
        value: The invalid value (will be sanitized)
        error_message: Validation error message
        logger_name: Name of the logger to use
    """
    logger = logging.getLogger(logger_name)

    # Sanitize sensitive values
    safe_value = str(value)[:100] if not _is_sensitive_field(field) else "[REDACTED]"

    logger.warning(
        f"Validation failed for field '{field}': {error_message}",
        extra={"field": field, "value": safe_value, "error": error_message},
    )


def _is_sensitive_field(field_name: str) -> bool:
    """Check if a field contains sensitive data that should not be logged.

    Args:
        field_name: Name of the field to check

    Returns:
        True if field is sensitive, False otherwise
    """
    sensitive_fields = {
        "password",
        "secret",
        "key",
        "token",
        "credential",
        "auth",
        "session",
        "cookie",
    }

    field_lower = field_name.lower()
    return any(sensitive in field_lower for sensitive in sensitive_fields)
