"""
POST /v1/enrich   — batch parse + aggregate analytics
POST /v1/profile  — financial profile for credit scoring

Requests with < 500 SMS are processed synchronously.
Requests with >= 500 SMS are queued as async jobs and return a job_id.
"""
from __future__ import annotations

import time
from typing import Annotated

import parser as p
from categorizer.pipeline import categorize
from categorizer.taxonomy import BY_SLUG
from enricher.analytics import compute_profile, compute_summary
from enricher import jobs as job_store
from fastapi import APIRouter, BackgroundTasks, Depends

from api.auth import get_api_key
from api.models import (
    CategoryBreakdown,
    CounterpartySummary,
    DateRange,
    EnrichRequest,
    EnrichResponse,
    EnrichSummary,
    ProfileResponse,
    RiskSignal,
    new_request_id,
)
from api.rate_limit import rate_limit

router = APIRouter()

_ASYNC_THRESHOLD = 500  # SMS count above which we go async


def _parse_and_categorize(messages) -> list[dict]:
    tx_dicts = []
    for msg in messages:
        result = p.parse(msg.sms_text, sender_id=msg.sender_id)
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
    return tx_dicts


def _build_enrich_summary(data: dict) -> EnrichSummary:
    return EnrichSummary(
        total_income=data["total_income"],
        total_expenses=data["total_expenses"],
        net_cash_flow=data["net_cash_flow"],
        transaction_count=data["transaction_count"],
        category_breakdown={
            k: CategoryBreakdown(**v)
            for k, v in data["category_breakdown"].items()
        },
        transaction_frequency_per_day=data["transaction_frequency_per_day"],
        unique_counterparties=data["unique_counterparties"],
        date_range=DateRange(**data["date_range"]),
    )


@router.post(
    "/enrich",
    response_model=EnrichResponse,
    summary="Batch parse + aggregate analytics",
    tags=["enrich"],
    responses={
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit)],
)
async def enrich(
    body: EnrichRequest,
    background_tasks: BackgroundTasks,
    api_key: Annotated[str, Depends(get_api_key)],
):
    """
    Parse and categorize up to 1,000 MoMo SMS messages and return aggregate
    financial analytics — total income, expenses, net cash flow, category
    breakdown, counterparty count, and date range.

    **Async mode:** Requests with 500+ messages are queued immediately and
    processed in the background. The response contains a `job_id`; poll
    `GET /v1/jobs/{job_id}` for the result or provide a `webhook_url`.
    """
    request_id = new_request_id()

    # Large batches → async
    if len(body.messages) >= _ASYNC_THRESHOLD:
        messages_raw = [
            {"sms_text": m.sms_text, "sender_id": m.sender_id}
            for m in body.messages
        ]
        job = job_store.create_job(
            message_count=len(body.messages),
            webhook_url=body.webhook_url,
        )
        background_tasks.add_task(
            job_store.run_enrich_job, job, messages_raw, "enrich"
        )
        return EnrichResponse(
            request_id=request_id,
            job_id=job.job_id,
            status="queued",
        )

    # Small batches → sync
    t0 = time.monotonic()
    tx_dicts = _parse_and_categorize(body.messages)
    data = compute_summary(tx_dicts)
    elapsed = round((time.monotonic() - t0) * 1000, 2)

    return EnrichResponse(
        request_id=request_id,
        processing_time_ms=elapsed,
        summary=_build_enrich_summary(data),
    )


@router.post(
    "/profile",
    response_model=ProfileResponse,
    summary="Financial profile for credit scoring",
    tags=["enrich"],
    responses={
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit)],
)
async def profile(
    body: EnrichRequest,
    background_tasks: BackgroundTasks,
    api_key: Annotated[str, Depends(get_api_key)],
):
    """
    Parse and categorize up to 1,000 MoMo SMS and return a higher-level
    financial profile suitable for credit scoring and lending decisions:

    - **avg_monthly_income** — average GHS income per month
    - **income_consistency_cv** — coefficient of variation (lower = more stable)
    - **expense_ratio** — expenses / income
    - **business_activity_score** — 0–100 score
    - **revenue_trend** — growing / stable / declining
    - **risk_signals** — list of detected risk flags

    **Note:** MomoParse provides structured data; lending decisions remain
    with the lender.
    """
    request_id = new_request_id()

    if len(body.messages) >= _ASYNC_THRESHOLD:
        messages_raw = [
            {"sms_text": m.sms_text, "sender_id": m.sender_id}
            for m in body.messages
        ]
        job = job_store.create_job(
            message_count=len(body.messages),
            webhook_url=body.webhook_url,
        )
        background_tasks.add_task(
            job_store.run_enrich_job, job, messages_raw, "profile"
        )
        return ProfileResponse(
            request_id=request_id,
            job_id=job.job_id,
            status="queued",
        )

    t0 = time.monotonic()
    tx_dicts = _parse_and_categorize(body.messages)
    data = compute_profile(tx_dicts)
    elapsed = round((time.monotonic() - t0) * 1000, 2)

    return ProfileResponse(
        request_id=request_id,
        processing_time_ms=elapsed,
        avg_monthly_income=data["avg_monthly_income"],
        income_consistency_cv=data["income_consistency_cv"],
        expense_ratio=data["expense_ratio"],
        top_counterparties=[CounterpartySummary(**cp) for cp in data["top_counterparties"]],
        business_activity_score=data["business_activity_score"],
        revenue_trend=data["revenue_trend"],
        risk_signals=[RiskSignal(**rs) for rs in data["risk_signals"]],
        months_of_data=data["months_of_data"],
        summary=_build_enrich_summary(data["summary"]),
    )
