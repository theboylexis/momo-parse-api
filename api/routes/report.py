"""
POST /v1/report — monthly financial report with insights and recommendations.

Accepts up to 1,000 MoMo SMS messages and returns:
- Per-month income/expense/savings breakdown
- Spending insights (top categories, trends, fee alerts)
- Savings analysis with rate
- Budget recommendations
- Financial health score (0–100)
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from api.auth import get_api_key
from api.models import (
    CategoryBreakdown,
    DateRange,
    EnrichRequest,
    EnrichSummary,
    FinancialIndexes,
    Insight,
    MonthBreakdown,
    Recommendation,
    ReportResponse,
    SavingsAnalysis,
    new_request_id,
)
from api.rate_limit import rate_limit
from api.routes.enrich import _parse_and_categorize, _build_enrich_summary
from enricher.analytics import compute_report
from enricher import jobs as job_store

router = APIRouter()

_ASYNC_THRESHOLD = 500


@router.post(
    "/report",
    response_model=ReportResponse,
    summary="Monthly financial report with insights & recommendations",
    tags=["report"],
    responses={
        401: {"description": "Missing or invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit)],
)
async def report(
    body: EnrichRequest,
    background_tasks: BackgroundTasks,
    api_key: Annotated[str, Depends(get_api_key)],
):
    """
    Parse and categorize up to 1,000 MoMo SMS messages and generate a
    **monthly financial report** designed to help users plan their finances:

    - **months** — per-month income, expenses, net savings, and savings rate
    - **insights** — spending highlights, trends, fee alerts
    - **savings_analysis** — overall savings rate and net position
    - **recommendations** — actionable budget advice based on spending patterns
    - **financial_health_score** — 0–100 score summarizing financial wellness

    **Async mode:** Requests with 500+ messages are queued and processed in
    the background. Poll `GET /v1/jobs/{job_id}` for the result.
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
            job_store.run_enrich_job, job, messages_raw, "report",
            body.window_months,
        )
        return ReportResponse(
            request_id=request_id,
            job_id=job.job_id,
            status="queued",
        )

    # Small batches → sync
    t0 = time.monotonic()
    tx_dicts = _parse_and_categorize(body.messages)
    data = compute_report(tx_dicts, window_months=body.window_months)
    elapsed = round((time.monotonic() - t0) * 1000, 2)

    return ReportResponse(
        request_id=request_id,
        processing_time_ms=elapsed,
        months=[MonthBreakdown(**m) for m in data["months"]],
        insights=[Insight(**i) for i in data["insights"]],
        savings_analysis=SavingsAnalysis(**data["savings_analysis"]),
        recommendations=[Recommendation(**r) for r in data["recommendations"]],
        financial_health_score=data["financial_health_score"],
        financial_indexes=FinancialIndexes(**data["financial_indexes"]),
        data_confidence=data["data_confidence"],
        summary=_build_enrich_summary(data["summary"]),
    )
