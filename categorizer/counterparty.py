"""
Layer 3 — Counterparty Intelligence.

Maintains a profile of each counterparty (keyed by phone number or name)
tracking the distribution of categories assigned to transactions with them.
When enough evidence accumulates, this becomes a strong prior.

In production this would live in a database shared across API users
(anonymized). For now it's an in-memory store with optional file persistence.

Data moat: the more API calls, the smarter the profiles become.
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from typing import Optional

_STORE: dict[str, Counter] = defaultdict(Counter)
_PERSIST_PATH = os.path.join(os.path.dirname(__file__), "counterparty_profiles.json")

# Minimum observations before we trust the profile
_MIN_OBSERVATIONS = 3
# Minimum majority fraction to fire
_MIN_MAJORITY = 0.70


def record(counterparty_key: str, category: str) -> None:
    """Record that a transaction with this counterparty was assigned this category."""
    if counterparty_key:
        _STORE[counterparty_key][category] += 1


def predict(counterparty_key: Optional[str]) -> tuple[str, float] | None:
    """
    Return (category_slug, confidence) if the counterparty profile is strong
    enough to suggest a category, else None.
    """
    if not counterparty_key:
        return None

    counter = _STORE.get(counterparty_key)
    if not counter:
        return None

    total = sum(counter.values())
    if total < _MIN_OBSERVATIONS:
        return None

    top_category, top_count = counter.most_common(1)[0]
    fraction = top_count / total
    if fraction >= _MIN_MAJORITY:
        # Scale confidence: 70% majority → 0.75 conf, 100% majority → 0.95 conf
        confidence = 0.75 + (fraction - _MIN_MAJORITY) * (0.20 / (1.0 - _MIN_MAJORITY))
        return top_category, round(min(confidence, 0.95), 3)

    return None


def _make_key(phone: Optional[str], name: Optional[str]) -> Optional[str]:
    """Prefer phone (more stable), fall back to normalized name."""
    if phone and len(phone.strip()) > 4:
        return phone.strip()
    if name and len(name.strip()) > 1:
        return name.strip().upper()
    return None


def load() -> None:
    """Load persisted profiles from disk (call at app startup)."""
    if not os.path.exists(_PERSIST_PATH):
        return
    with open(_PERSIST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for key, counts in data.items():
        _STORE[key] = Counter(counts)


def save() -> None:
    """Persist profiles to disk."""
    data = {k: dict(v) for k, v in _STORE.items()}
    with open(_PERSIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def profile_count() -> int:
    return len(_STORE)
