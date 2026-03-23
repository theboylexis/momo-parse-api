"""
Rate limiting via a FastAPI Depends dependency (no decorator magic).

Uses an in-memory sliding-window counter per (api_key, route).
Swap _store for a Redis-backed implementation when deploying to production.

Tiers:
  sandbox  — 100 calls / day
  free     — 1 000 calls / month + 10 / minute burst
  starter  — 50 000 calls / month + 100 / minute burst
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from api.auth import get_api_key, get_tier

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# In-memory store: key → deque of call timestamps (seconds since epoch)      #
# --------------------------------------------------------------------------- #
_store: dict[str, deque[float]] = defaultdict(deque)


def _sliding_window(key: str, limit: int, window_seconds: int) -> bool:
    """
    Return True if the call is within the limit, False if the limit is exceeded.
    Modifies _store in-place.
    """
    now = time.monotonic()
    q = _store[key]
    cutoff = now - window_seconds
    while q and q[0] < cutoff:
        q.popleft()
    if len(q) >= limit:
        return False
    q.append(now)
    return True


# --------------------------------------------------------------------------- #
# Tier configuration                                                           #
# --------------------------------------------------------------------------- #
_TIER_WINDOWS: dict[str, list[tuple[int, int]]] = {
    # list of (limit, window_seconds)
    "sandbox": [(100, 86_400)],             # 100 / day
    "free":    [(10, 60), (1_000, 2_592_000)],   # 10/min + 1000/month
    "starter": [(100, 60), (50_000, 2_592_000)], # 100/min + 50k/month
}


def _get_tier_windows(tier: str) -> list[tuple[int, int]]:
    return _TIER_WINDOWS.get(tier, _TIER_WINDOWS["free"])


# --------------------------------------------------------------------------- #
# FastAPI dependency                                                           #
# --------------------------------------------------------------------------- #
def rate_limit(request: Request, api_key: Annotated[str, Depends(get_api_key)]):
    """
    Dependency that enforces sliding-window rate limits based on the caller's tier.
    Raises 429 if any window is exceeded.
    """
    tier = get_tier(api_key)
    for limit, window in _get_tier_windows(tier):
        store_key = f"{api_key}:{window}"
        if not _sliding_window(store_key, limit, window):
            label = f"{limit} requests per {'minute' if window == 60 else 'day' if window == 86400 else 'month'}"
            logger.warning("Rate limit hit: %s (%s)", api_key[:8] + "…", label)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded: {label}.",
                    "documentation_url": "https://docs.momoparse.com/rate-limits",
                },
            )
