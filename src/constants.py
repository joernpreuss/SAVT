"""Application constants."""

from typing import Final

# Field length constants
MAX_NAME_LENGTH: Final = 100
MAX_KIND_LENGTH: Final = 50
MIN_SECRET_KEY_LENGTH: Final = 32

# Network constants
DEFAULT_PORT: Final = 8000

# HTTP status codes (commonly used)
HTTP_BAD_REQUEST: Final = 400
HTTP_NOT_FOUND: Final = 404
HTTP_CONFLICT: Final = 409
HTTP_INTERNAL_SERVER_ERROR: Final = 500
