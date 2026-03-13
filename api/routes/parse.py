"""
POST /v1/parse        — single SMS parse
POST /v1/parse/batch  — up to 100 SMS in one call
"""
from __future__ import annotations

import time
from typing import Annotated

from fastapi import APIRouter, Depends

import parser as p
from api.auth import get_api_key
from api.models import (
    BatchParseRequest,
    BatchParseResponse,
    CounterpartyModel,
    ParseRequest,
    ParseResponse,
    new_request_id,
)
from api.rate_limit import rate_limit

router = APIRouter()


def _to_response(
    req: ParseRequest,
    result: p.ParseResult,
    request_id: str,
    processing_time_ms: float,
) -> ParseResponse:
    return ParseResponse(
        request_id=request_id,
        processing_time_ms=processing_time_ms,
        telco=result.telco,
        tx_type=result.tx_type,
        template_id=result.template_id,
        confidence=result.confidence,
        amount=result.amount,
        currency=result.currency,
        balance=result.balance,
        fee=result.fee,
        counterparty=CounterpartyModel(
            name=result.counterparty_name,
            phone=result.counterparty_phone,
        ),
        tx_id=result.tx_id,
        reference=result.reference,
        date=result.date,
        time=result.time,
        metadata=req.metadata,
    )


@router.post(
    "/parse",
    response_model=ParseResponse,
    summary="Parse a single MoMo SMS",
    tags=["parse"],
    responses={
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Validation error (missing required fields)"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit)],
)
async def parse_single(
    body: ParseRequest,
    api_key: Annotated[str, Depends(get_api_key)],
):
    """
    Parse a single raw MoMo SMS string and return structured transaction data.

    - **sms_text**: Raw SMS text (required)
    - **sender_id**: Originating sender ID for accurate telco detection (optional)
    - **metadata**: Arbitrary key-value pairs echoed back in the response (optional)
    """
    t0 = time.monotonic()
    result = p.parse(body.sms_text, sender_id=body.sender_id)
    elapsed = round((time.monotonic() - t0) * 1000, 2)
    return _to_response(body, result, new_request_id(), elapsed)


@router.post(
    "/parse/batch",
    response_model=BatchParseResponse,
    summary="Parse up to 100 MoMo SMS in a single request",
    tags=["parse"],
    responses={
        401: {"description": "Missing or invalid API key"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    },
    dependencies=[Depends(rate_limit)],
)
async def parse_batch(
    body: BatchParseRequest,
    api_key: Annotated[str, Depends(get_api_key)],
):
    """
    Parse an array of MoMo SMS messages (max 100) in a single round-trip.
    Each message is parsed independently; results are returned in the same order.
    """
    t0 = time.monotonic()
    batch_id = new_request_id()
    results = []
    for msg in body.messages:
        item_start = time.monotonic()
        result = p.parse(msg.sms_text, sender_id=msg.sender_id)
        item_ms = round((time.monotonic() - item_start) * 1000, 2)
        results.append(_to_response(msg, result, new_request_id(), item_ms))

    total_ms = round((time.monotonic() - t0) * 1000, 2)
    return BatchParseResponse(
        request_id=batch_id,
        processing_time_ms=total_ms,
        count=len(results),
        results=results,
    )
