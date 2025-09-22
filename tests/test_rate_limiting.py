"""Tests for rate limiting functionality."""

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.infrastructure.database.database import get_session
from src.main import app


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_rate_limiting_general_endpoint(client: TestClient):
    """Test rate limiting on general API endpoints.

    Requirements:
    - Rate limiting: General endpoints limited to 100 req/min per IP
    """
    # Make many requests quickly to trigger rate limiting
    # We'll mock the rate limiter to use lower limits for testing
    from src.rate_limiting import rate_limiter

    # Enable rate limiting for this test (disabled by default in conftest.py)
    rate_limiter.enable()
    rate_limiter.reset()

    # Temporarily reduce limits for testing
    original_limits = rate_limiter.set_limits_for_testing(general=3)

    try:
        responses = []
        # Make requests that should trigger rate limiting
        for _ in range(5):
            response = client.get("/api/v1/properties")
            responses.append(response.status_code)

        # First 3 should succeed, 4th and 5th should be rate limited
        assert responses[:3] == [200, 200, 200]
        assert responses[3] == 429  # Too Many Requests
        assert responses[4] == 429  # Too Many Requests

    finally:
        # Restore original limits
        rate_limiter.restore_limits(original_limits)
        # Clear rate limiting data
        rate_limiter.reset()


def test_rate_limiting_write_operations(client: TestClient, timestamp_str: str):
    """Test rate limiting on write operations.

    Requirements:
    - Rate limiting: Write operations limited to 30 req/min per IP
    """
    from src.rate_limiting import rate_limiter

    # Enable rate limiting for this test
    rate_limiter.enable()
    rate_limiter.reset()

    # Temporarily reduce limits for testing
    original_limits = rate_limiter.set_limits_for_testing(write=2)

    try:
        responses = []
        # Make POST requests that should trigger rate limiting
        for i in range(4):
            response = client.post(
                "/api/v1/properties",
                json={"name": f"test_rate_limit_write_{timestamp_str}_{i}"},
            )
            responses.append(response.status_code)

        # First 2 should succeed, 3rd and 4th should be rate limited
        assert responses[:2] == [201, 201]
        assert responses[2] == 429  # Too Many Requests
        assert responses[3] == 429  # Too Many Requests

    finally:
        # Restore original limits
        rate_limiter.restore_limits(original_limits)
        # Clear rate limiting data
        rate_limiter.reset()


def test_rate_limiting_headers(client: TestClient):
    """Test that rate limiting headers are included in responses.

    Requirements:
    - Rate limiting headers: X-RateLimit-* headers in responses
    """
    response = client.get("/api/v1/properties")
    assert response.status_code == 200

    # Check rate limiting headers are present
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers

    # Verify header values are reasonable
    limit = int(response.headers["X-RateLimit-Limit"])
    remaining = int(response.headers["X-RateLimit-Remaining"])
    reset_time = int(response.headers["X-RateLimit-Reset"])

    assert limit > 0
    assert remaining >= 0
    assert remaining <= limit
    assert reset_time > int(time.time())  # Reset time should be in the future


def test_rate_limiting_different_ips():
    """Test that rate limiting is per-IP (different IPs have separate limits)."""
    from src.rate_limiting import rate_limiter

    # Enable rate limiting for this test
    rate_limiter.enable()
    rate_limiter.reset()

    # Temporarily reduce limits for testing
    original_limits = rate_limiter.set_limits_for_testing(general=2)

    try:
        # Simulate requests from different IPs
        with patch("src.rate_limiting.Request") as mock_request:
            # First IP
            mock_request.client.host = "192.168.1.1"
            mock_request.url.path = "/api/v1/properties"
            mock_request.method = "GET"
            mock_request.headers = {}

            # Should allow 2 requests for first IP
            rate_limiter.check_rate_limit(mock_request)
            rate_limiter.check_rate_limit(mock_request)

            # Third request from same IP should fail
            from fastapi import HTTPException

            with pytest.raises(HTTPException):
                rate_limiter.check_rate_limit(mock_request)

            # But requests from different IP should still work
            mock_request.client.host = "192.168.1.2"
            rate_limiter.check_rate_limit(mock_request)  # Should not raise

    finally:
        # Restore original limits
        rate_limiter.restore_limits(original_limits)
        # Clear rate limiting data
        rate_limiter.reset()


def test_rate_limiting_window_expiry():
    """Test that rate limiting window resets after time passes."""
    from src.rate_limiting import rate_limiter

    # Test that old requests are cleaned up
    ip = "192.168.1.100"

    # Add some old requests (more than 60 seconds ago)
    old_time = time.time() - 120  # 2 minutes ago
    rate_limiter.add_request_timestamp(ip, old_time)
    rate_limiter.add_request_timestamp(ip, old_time + 1)
    rate_limiter.add_request_timestamp(ip, old_time + 2)

    # Check that old requests are cleaned up when getting count
    assert rate_limiter.get_request_count(ip) == 0


def test_rate_limiting_error_response_format(client: TestClient):
    """Test that rate limiting error responses have correct format.

    Requirements:
    - Error format: 429 responses should include retry information
    """
    from src.rate_limiting import rate_limiter

    # Enable rate limiting for this test
    rate_limiter.enable()
    rate_limiter.reset()

    # Temporarily reduce limits for testing
    original_limits = rate_limiter.set_limits_for_testing(general=1)

    try:
        # First request should succeed
        response1 = client.get("/api/v1/properties")
        assert response1.status_code == 200

        # Second request should be rate limited
        response2 = client.get("/api/v1/properties")
        assert response2.status_code == 429

        # Check error response format
        error_data = response2.json()
        assert "error" in error_data
        assert "limit" in error_data
        assert "retry_after" in error_data
        assert "current_requests" in error_data

        # Check headers
        assert "Retry-After" in response2.headers
        assert response2.headers["Retry-After"] == "60"

    finally:
        # Restore original limits
        rate_limiter.restore_limits(original_limits)
        # Clear rate limiting data
        rate_limiter.reset()


def test_rate_limiting_non_api_routes_not_limited(client: TestClient):
    """Test that non-API routes are not rate limited.

    Requirements:
    - Rate limiting: Only /api/ routes should be rate limited
    """
    # HTML routes should not be rate limited
    response = client.get("/")
    assert response.status_code == 200

    # Should not have rate limiting headers
    assert "X-RateLimit-Limit" not in response.headers
