"""Simple in-memory rate limiting for SAVT API endpoints."""

import time
from collections import defaultdict
from typing import Final

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from .request_utils import get_client_ip, is_api_request


class RateLimiter:
    """Simple in-memory rate limiter using sliding window approach."""

    def __init__(self):
        # Store request timestamps for each IP
        self._requests: dict[str, list[float]] = defaultdict(list)
        # Default rate limits (requests per minute)
        self._limits: Final = {
            "general": 100,  # General API endpoints
            "write": 30,  # Write operations (POST, PUT, DELETE)
            "bulk": 10,  # Bulk operations
        }
        # Flag to disable rate limiting (for testing)
        self._enabled: bool = True

    def disable(self) -> None:
        """Disable rate limiting (for testing)."""
        self._enabled = False

    def enable(self) -> None:
        """Enable rate limiting."""
        self._enabled = True

    def reset(self) -> None:
        """Reset all rate limiting data."""
        self._requests.clear()

    def set_limits_for_testing(self, **limits: int) -> dict[str, int]:
        """Set rate limits for testing purposes. Returns original limits."""
        original = self._limits.copy()
        for limit_type, value in limits.items():
            if limit_type in self._limits:
                self._limits[limit_type] = value
        return original

    def restore_limits(self, original_limits: dict[str, int]) -> None:
        """Restore original rate limits after testing."""
        self._limits.update(original_limits)

    def get_request_count(self, ip: str) -> int:
        """Get current request count for an IP (for testing)."""
        self._clean_old_requests(ip)
        return len(self._requests[ip])

    def add_request_timestamp(self, ip: str, timestamp: float) -> None:
        """Add a request timestamp for testing purposes."""
        self._requests[ip].append(timestamp)

    def get_rate_limit_info(self, request: Request) -> tuple[int, int, int]:
        """Get rate limit information for a request.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (limit, remaining, reset_time)
        """
        client_ip = get_client_ip(request)
        limit, _ = self._get_rate_limit_for_path(str(request.url.path), request.method)

        self._clean_old_requests(client_ip)
        remaining = max(0, limit - len(self._requests[client_ip]))
        reset_time = int(time.time()) + 60

        return limit, remaining, reset_time

    def _clean_old_requests(self, ip: str, window_seconds: int = 60) -> None:
        """Remove requests older than the time window."""
        cutoff_time = time.time() - window_seconds
        self._requests[ip] = [
            timestamp for timestamp in self._requests[ip] if timestamp > cutoff_time
        ]

    def _get_rate_limit_for_path(self, path: str, method: str) -> tuple[int, str]:
        """Determine rate limit based on path and method."""
        # Write operations get stricter limits
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            if "/bulk/" in path:
                return self._limits["bulk"], "bulk"
            return self._limits["write"], "write"

        # Read operations get general limits
        return self._limits["general"], "general"

    def check_rate_limit(self, request: Request) -> None:
        """Check if request should be rate limited."""
        # Skip rate limiting if disabled (for testing)
        if not self._enabled:
            return

        # Get client IP with proxy support
        client_ip = get_client_ip(request)

        # Get rate limit for this endpoint
        limit, limit_type = self._get_rate_limit_for_path(
            str(request.url.path), request.method
        )

        # Clean old requests and check current count
        self._clean_old_requests(client_ip)
        current_requests = len(self._requests[client_ip])

        if current_requests >= limit:
            # Rate limit exceeded
            retry_after = 60  # Wait 1 minute before retrying
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": limit,
                    "limit_type": limit_type,
                    "retry_after": retry_after,
                    "current_requests": current_requests,
                },
                headers={"Retry-After": str(retry_after)},
            )

        # Record this request
        self._requests[client_ip].append(time.time())


# Global rate limiter instance
rate_limiter = RateLimiter()


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware for FastAPI."""
    # Only apply rate limiting to API endpoints
    if is_api_request(request):
        try:
            rate_limiter.check_rate_limit(request)
        except HTTPException as e:
            # Return JSON error response for rate limiting
            return JSONResponse(
                status_code=e.status_code,
                content=e.detail,
                headers=e.headers or {},
            )

    # Process the request
    response = await call_next(request)

    # Add rate limit headers to API responses
    if is_api_request(request):
        limit, remaining, reset_time = rate_limiter.get_rate_limit_info(request)

        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

    return response
