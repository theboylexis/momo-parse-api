"""
Async job store for large enrichment requests (500+ SMS).

Uses PostgreSQL when DATABASE_URL is set (via enable_db()), otherwise
falls back to an in-memory dict. Both paths expose the same API.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Job:
    job_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    webhook_url: Optional[str] = None
    message_count: int = 0


# ── Storage backend ──────────────────────────────────────────────────────────
# In-memory fallback (default). Replaced by DB when enable_db() is called.
_jobs: dict[str, Job] = {}
_use_db = False


def enable_db() -> None:
    """Switch from in-memory to database-backed storage."""
    global _use_db
    _use_db = True


def create_job(message_count: int, webhook_url: Optional[str] = None) -> Job:
    job = Job(
        job_id=str(uuid.uuid4()),
        message_count=message_count,
        webhook_url=webhook_url,
    )
    if _use_db:
        from db.engine import get_session
        from db.models import JobRecord

        with get_session() as session:
            session.add(JobRecord(
                job_id=job.job_id,
                status=job.status.value,
                webhook_url=webhook_url,
                message_count=message_count,
            ))
            session.commit()
    else:
        _jobs[job.job_id] = job
    logger.info("Job %s created (%d messages)", job.job_id, message_count)
    return job


def get_job(job_id: str) -> Optional[Job]:
    if _use_db:
        from db.engine import get_session
        from db.models import JobRecord

        with get_session() as session:
            row = session.query(JobRecord).filter_by(job_id=job_id).first()
            if not row:
                return None
            return Job(
                job_id=row.job_id,
                status=JobStatus(row.status),
                created_at=row.created_at.isoformat() if row.created_at else "",
                completed_at=row.completed_at.isoformat() if row.completed_at else None,
                result=row.result,
                error=row.error,
                webhook_url=row.webhook_url,
                message_count=row.message_count or 0,
            )
    return _jobs.get(job_id)


def _set_complete(job: Job, result: dict[str, Any]) -> None:
    job.status = JobStatus.COMPLETE
    job.result = result
    job.completed_at = datetime.now(timezone.utc).isoformat()
    if _use_db:
        from db.engine import get_session
        from db.models import JobRecord

        with get_session() as session:
            row = session.query(JobRecord).filter_by(job_id=job.job_id).first()
            if row:
                row.status = JobStatus.COMPLETE.value
                row.result = result
                row.completed_at = datetime.now(timezone.utc)
                session.commit()
    logger.info("Job %s complete", job.job_id)


def _set_failed(job: Job, error: str) -> None:
    job.status = JobStatus.FAILED
    job.error = error
    job.completed_at = datetime.now(timezone.utc).isoformat()
    if _use_db:
        from db.engine import get_session
        from db.models import JobRecord

        with get_session() as session:
            row = session.query(JobRecord).filter_by(job_id=job.job_id).first()
            if row:
                row.status = JobStatus.FAILED.value
                row.error = error
                row.completed_at = datetime.now(timezone.utc)
                session.commit()
    logger.error("Job %s failed: %s", job.job_id, error)


async def _deliver_webhook(webhook_url: str, payload: dict[str, Any]) -> None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(webhook_url, json=payload)
    except Exception:
        logger.warning("Webhook delivery failed for %s", webhook_url)


async def run_enrich_job(job: Job, messages: list[dict], mode: str = "enrich") -> None:
    """
    Background task: parse + enrich/profile all messages, store result, fire webhook.
    mode: "enrich" | "profile"
    """
    import time

    import parser as p
    from categorizer.pipeline import categorize
    from categorizer.taxonomy import BY_SLUG
    from enricher.analytics import compute_profile, compute_report, compute_summary

    job.status = JobStatus.PROCESSING
    t0 = time.monotonic()

    try:
        tx_dicts = []
        for msg in messages:
            result = p.parse(msg["sms_text"], sender_id=msg.get("sender_id"))
            cat_slug, cat_conf = categorize(
                tx_type=result.tx_type,
                amount=result.amount,
                reference=result.reference,
                counterparty_name=result.counterparty_name,
                counterparty_phone=result.counterparty_phone,
                fee=result.fee,
            )
            tx_dicts.append({
                "tx_type": result.tx_type,
                "amount": result.amount,
                "category": cat_slug,
                "category_label": BY_SLUG[cat_slug].label if cat_slug in BY_SLUG else None,
                "category_confidence": cat_conf,
                "counterparty_name": result.counterparty_name,
                "counterparty_phone": result.counterparty_phone,
                "reference": result.reference,
                "date": result.date,
                "fee": result.fee,
                "telco": result.telco,
                "tx_id": result.tx_id,
            })

        elapsed = round((time.monotonic() - t0) * 1000, 2)

        if mode == "profile":
            analytics = compute_profile(tx_dicts)
        elif mode == "report":
            analytics = compute_report(tx_dicts)
        else:
            analytics = compute_summary(tx_dicts)

        result_payload = {
            "job_id": job.job_id,
            "status": "complete",
            "processing_time_ms": elapsed,
            "message_count": len(tx_dicts),
            "data": analytics,
        }

        _set_complete(job, result_payload)

        if job.webhook_url:
            await _deliver_webhook(job.webhook_url, result_payload)

    except Exception as exc:
        _set_failed(job, str(exc))
        if job.webhook_url:
            await _deliver_webhook(job.webhook_url, {
                "job_id": job.job_id,
                "status": "failed",
                "error": str(exc),
            })
