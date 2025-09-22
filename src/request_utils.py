"""Utilities for handling FastAPI requests."""

from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Extract client IP address with proxy support.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address as string. Returns "unknown" if unable to determine.

    Notes:
        - Checks X-Forwarded-For header first (for load balancers/proxies)
        - Falls back to X-Real-IP header (for nginx proxy)
        - Finally uses request.client.host (direct connection)
        - Returns "unknown" if none of these are available
    """
    # Check X-Forwarded-For header (comma-separated list, first is original client)
    forwarded_for: str | None = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the comma-separated list
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # Check X-Real-IP header (single IP, set by nginx and similar proxies)
    real_ip: str | None = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client connection
    if request.client and request.client.host:
        return str(request.client.host)

    # Last resort if nothing is available
    return "unknown"


def is_api_request(request: Request) -> bool:
    """Check if request is to an API endpoint.

    Args:
        request: FastAPI request object

    Returns:
        True if request path starts with /api/, False otherwise
    """
    return str(request.url.path).startswith("/api/")


def is_htmx_request(request: Request) -> bool:
    """Check if request is an HTMX request.

    Args:
        request: FastAPI request object

    Returns:
        True if request contains HX-Request header, False otherwise
    """
    return "HX-Request" in request.headers
