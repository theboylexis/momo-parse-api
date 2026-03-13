"""
Typed exceptions raised by MomoParseClient and AsyncMomoParseClient.
"""
from __future__ import annotations


class MomoParseError(Exception):
    """Base exception for all MomoParse SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, error_code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


class AuthError(MomoParseError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class RateLimitError(MomoParseError):
    """Raised when the rate limit is exceeded (HTTP 429)."""


class ValidationError(MomoParseError):
    """Raised when the request payload fails validation (HTTP 422)."""


class ServerError(MomoParseError):
    """Raised on unexpected server errors (HTTP 5xx)."""
