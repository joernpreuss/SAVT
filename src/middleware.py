import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from .logging_utils import log_api_request


async def log_requests_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware to log all HTTP requests with timing information.

    Args:
        request: FastAPI request object
        call_next: Next middleware/route handler in the chain

    Returns:
        Response from the route handler
    """
    start_time = time.time()

    # Call the route handler
    response = await call_next(request)

    # Calculate processing time
    process_time = (time.time() - start_time) * 1000  # Convert to milliseconds

    # Log the request
    log_api_request(
        request=request,
        response_status=response.status_code,
        process_time_ms=process_time,
    )

    return response
