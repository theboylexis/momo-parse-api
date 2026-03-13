"""
API key authentication.

Keys are read from the environment variable MOMOPARSE_API_KEYS as a
comma-separated list (e.g. "key-abc123,key-def456").

The special value "SANDBOX" is always accepted and maps to the sandbox tier.

Production note: swap _load_keys() for a PostgreSQL lookup when ready.
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import Header, HTTPException, status

# Built-in sandbox key — never expires, rate-limited to 100 calls / IP / day
SANDBOX_KEY = "sk-sandbox-momoparse"

_TIER_MAP: dict[str, str] = {
    SANDBOX_KEY: "sandbox",
}


def _load_keys() -> set[str]:
    raw = os.getenv("MOMOPARSE_API_KEYS", "")
    keys = {k.strip() for k in raw.split(",") if k.strip()}
    keys.add(SANDBOX_KEY)
    return keys


_VALID_KEYS: set[str] = _load_keys()


def get_api_key(x_api_key: Optional[str] = Header(default=None)) -> str:
    """
    FastAPI dependency — extracts and validates X-API-Key header.
    Returns the key if valid; raises 401 otherwise.
    """
    if not x_api_key or x_api_key not in _VALID_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_API_KEY",
                "message": "Missing or invalid X-API-Key header.",
                "documentation_url": "https://docs.momoparse.com/authentication",
            },
        )
    return x_api_key


def get_tier(api_key: str) -> str:
    """Return the rate-limit tier for a validated key."""
    return _TIER_MAP.get(api_key, "free")
