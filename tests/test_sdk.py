"""
SDK integration tests.
Both sync and async clients are wired to the FastAPI app via httpx transports
so no live server is required.

Sync client transport: anyio BlockingPortal bridges sync->async for ASGI apps.
Async client transport: ASGITransport directly.
"""
from __future__ import annotations

import pytest
import anyio
import httpx
from httpx import ASGITransport

from api.main import app
from api.auth import SANDBOX_KEY
from sdk import MomoParseClient, AsyncMomoParseClient, ParseResult, BatchResult
from sdk.exceptions import AuthError, ValidationError

_MTN_TRANSFER = (
    "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
    "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
    "Reference: 1. Transaction ID: 76289975115. "
    "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
)


# ── Sync transport bridge ─────────────────────────────────────────────────────

class _PortalTransport(httpx.BaseTransport):
    """Routes httpx sync requests through an anyio BlockingPortal -> ASGI app.

    Reads the full async response body inside the portal so the returned
    httpx.Response carries a plain bytes body (SyncByteStream), satisfying
    httpx's internal assertion on sync clients.
    """

    def __init__(self, portal: anyio.from_thread.BlockingPortal):
        self._portal = portal
        self._asgi = ASGITransport(app=app)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        async def _call() -> httpx.Response:
            resp = await self._asgi.handle_async_request(request)
            content = b"".join([chunk async for chunk in resp.stream])
            return httpx.Response(
                status_code=resp.status_code,
                headers=resp.headers,
                content=content,
            )
        return self._portal.call(_call)


def _sync_client(api_key: str, portal: anyio.from_thread.BlockingPortal) -> MomoParseClient:
    return MomoParseClient(
        api_key=api_key,
        base_url="http://test",
        _transport=_PortalTransport(portal),
    )


# ── Sync client tests ─────────────────────────────────────────────────────────

def test_sync_parse_returns_parse_result():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            result = client.parse(_MTN_TRANSFER, sender_id="MobileMoney")
    assert isinstance(result, ParseResult)
    assert result.telco == "mtn"
    assert result.tx_type == "transfer_sent"
    assert result.amount == pytest.approx(35.00)
    assert result.counterparty.name == "ERNESTINA ANDOH"
    assert result.confidence == 1.0
    assert result.request_id != ""
    assert result.processing_time_ms >= 0


def test_sync_parse_unknown_sms():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            result = client.parse("Your OTP is 123456.")
    assert result.telco == "unknown"
    assert result.confidence == 0.0


def test_sync_parse_raises_auth_error_on_bad_key():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client("bad-key", portal) as client:
            with pytest.raises(AuthError) as exc_info:
                client.parse("hello")
    assert exc_info.value.status_code == 401
    assert exc_info.value.error_code == "INVALID_API_KEY"


def test_sync_parse_raises_validation_error_on_blank():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            with pytest.raises(ValidationError) as exc_info:
                client.parse("   ")
    assert exc_info.value.status_code == 422


def test_sync_parse_metadata_echoed():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            result = client.parse("hello", metadata={"user": "u-1"})
    assert result.metadata == {"user": "u-1"}


def test_sync_batch_returns_batch_result():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            result = client.parse_batch([
                {"sms_text": _MTN_TRANSFER, "sender_id": "MobileMoney"},
                {"sms_text": "Your OTP is 999."},
            ])
    assert isinstance(result, BatchResult)
    assert result.count == 2
    assert result.results[0].telco == "mtn"
    assert result.results[1].telco == "unknown"


def test_sync_batch_raises_validation_error_on_empty_list():
    with anyio.from_thread.start_blocking_portal() as portal:
        with _sync_client(SANDBOX_KEY, portal) as client:
            with pytest.raises(ValidationError):
                client.parse_batch([])


def test_sync_context_manager():
    with anyio.from_thread.start_blocking_portal() as portal:
        client = _sync_client(SANDBOX_KEY, portal)
        with client as c:
            result = c.parse("hello")
    assert isinstance(result, ParseResult)


# ── Async client tests ────────────────────────────────────────────────────────

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncMomoParseClient(
        api_key=SANDBOX_KEY,
        base_url="http://test",
        _transport=transport,
    ) as client:
        yield client


async def test_async_parse_returns_parse_result(async_client):
    result = await async_client.parse(_MTN_TRANSFER, sender_id="MobileMoney")
    assert isinstance(result, ParseResult)
    assert result.telco == "mtn"
    assert result.tx_type == "transfer_sent"
    assert result.amount == pytest.approx(35.00)
    assert result.counterparty.name == "ERNESTINA ANDOH"


async def test_async_parse_unknown_sms(async_client):
    result = await async_client.parse("Your OTP is 123456.")
    assert result.telco == "unknown"
    assert result.confidence == 0.0


async def test_async_parse_raises_auth_error():
    transport = ASGITransport(app=app)
    async with AsyncMomoParseClient(
        api_key="bad-key", base_url="http://test", _transport=transport
    ) as client:
        with pytest.raises(AuthError) as exc_info:
            await client.parse("hello")
    assert exc_info.value.status_code == 401


async def test_async_batch_returns_batch_result(async_client):
    result = await async_client.parse_batch([
        {"sms_text": _MTN_TRANSFER, "sender_id": "MobileMoney"},
        {"sms_text": "Not a momo SMS."},
    ])
    assert isinstance(result, BatchResult)
    assert result.count == 2
    assert len(result.results) == 2


async def test_async_context_manager():
    transport = ASGITransport(app=app)
    async with AsyncMomoParseClient(
        api_key=SANDBOX_KEY, base_url="http://test", _transport=transport
    ) as client:
        result = await client.parse("hello")
    assert isinstance(result, ParseResult)


# ── Model unit tests ──────────────────────────────────────────────────────────

def test_parse_result_repr():
    r = ParseResult(telco="mtn", tx_type="transfer_sent", amount=35.0, confidence=1.0)
    assert "mtn" in repr(r)
    assert "transfer_sent" in repr(r)


def test_batch_result_repr():
    b = BatchResult(
        request_id="x", api_version="v1",
        processing_time_ms=5.0, count=2, results=[]
    )
    assert "count=2" in repr(b)
