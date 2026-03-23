"""
Layer 3 — Counterparty Intelligence.

Maintains a profile of each counterparty (keyed by phone number or name)
tracking the distribution of categories assigned to transactions with them.
When enough evidence accumulates, this becomes a strong prior.

Uses PostgreSQL when DATABASE_URL is set (via enable_db()), otherwise
falls back to an in-memory store with optional JSON file persistence.

Data moat: the more API calls, the smarter the profiles become.
"""
from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

_STORE: dict[str, Counter] = defaultdict(Counter)
_PERSIST_PATH = os.path.join(os.path.dirname(__file__), "counterparty_profiles.json")
_use_db = False

# Minimum observations before we trust the profile
_MIN_OBSERVATIONS = 3
# Minimum majority fraction to fire
_MIN_MAJORITY = 0.70


def enable_db() -> None:
    """Switch from in-memory to database-backed storage."""
    global _use_db
    _use_db = True
    logger.info("Counterparty profiles using database storage")


def record(counterparty_key: str, category: str) -> None:
    """Record that a transaction with this counterparty was assigned this category."""
    if not counterparty_key:
        return

    if _use_db:
        from db.engine import get_session
        from db.models import CounterpartyProfile

        with get_session() as session:
            row = session.query(CounterpartyProfile).filter_by(key=counterparty_key).first()
            if row:
                counts = dict(row.counts) if row.counts else {}
                counts[category] = counts.get(category, 0) + 1
                row.counts = counts
            else:
                session.add(CounterpartyProfile(
                    key=counterparty_key,
                    counts={category: 1},
                ))
            session.commit()
    else:
        _STORE[counterparty_key][category] += 1


def predict(counterparty_key: Optional[str]) -> tuple[str, float] | None:
    """
    Return (category_slug, confidence) if the counterparty profile is strong
    enough to suggest a category, else None.
    """
    if not counterparty_key:
        return None

    if _use_db:
        from db.engine import get_session
        from db.models import CounterpartyProfile

        with get_session() as session:
            row = session.query(CounterpartyProfile).filter_by(key=counterparty_key).first()
            if not row or not row.counts:
                return None
            counter = Counter(row.counts)
    else:
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
    """Load persisted profiles from disk (no-op when using database)."""
    if _use_db:
        return
    if not os.path.exists(_PERSIST_PATH):
        return
    with open(_PERSIST_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for key, counts in data.items():
        _STORE[key] = Counter(counts)


def save() -> None:
    """Persist profiles to disk (no-op when using database)."""
    if _use_db:
        return
    data = {k: dict(v) for k, v in _STORE.items()}
    with open(_PERSIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def profile_count() -> int:
    if _use_db:
        from db.engine import get_session
        from db.models import CounterpartyProfile

        with get_session() as session:
            return session.query(CounterpartyProfile).count()
    return len(_STORE)
