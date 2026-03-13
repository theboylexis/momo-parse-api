"""
Integration tests for the FastAPI server.
Uses httpx.AsyncClient with ASGITransport — no live server needed.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.auth import SANDBOX_KEY

BASE = "http://test"
HEADERS = {"X-API-Key": SANDBOX_KEY}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body


# ── Auth ──────────────────────────────────────────────────────────────────────

async def test_parse_no_key_returns_401(client):
    r = await client.post("/v1/parse", json={"sms_text": "hello"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "INVALID_API_KEY"


async def test_parse_bad_key_returns_401(client):
    r = await client.post(
        "/v1/parse",
        json={"sms_text": "hello"},
        headers={"X-API-Key": "not-a-valid-key"},
    )
    assert r.status_code == 401


# ── Single parse ──────────────────────────────────────────────────────────────

async def test_parse_mtn_transfer_sent(client):
    sms = (
        "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
        "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
        "Reference: 1. Transaction ID: 76289975115. "
        "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
    )
    r = await client.post(
        "/v1/parse",
        json={"sms_text": sms, "sender_id": "MobileMoney"},
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["telco"] == "mtn"
    assert body["tx_type"] == "transfer_sent"
    assert body["amount"] == pytest.approx(35.00)
    assert body["counterparty"]["name"] == "ERNESTINA ANDOH"
    assert body["confidence"] == 1.0
    assert "request_id" in body
    assert "processing_time_ms" in body
    assert body["api_version"] == "v1"


async def test_parse_unknown_sms_returns_200_with_low_confidence(client):
    r = await client.post(
        "/v1/parse",
        json={"sms_text": "Your OTP is 482910. Valid for 5 minutes."},
        headers=HEADERS,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["telco"] == "unknown"
    assert body["confidence"] == 0.0


async def test_parse_blank_sms_returns_422(client):
    r = await client.post(
        "/v1/parse",
        json={"sms_text": "   "},
        headers=HEADERS,
    )
    assert r.status_code == 422


async def test_parse_missing_sms_text_returns_422(client):
    r = await client.post("/v1/parse", json={}, headers=HEADERS)
    assert r.status_code == 422


async def test_parse_metadata_echoed(client):
    r = await client.post(
        "/v1/parse",
        json={
            "sms_text": "Your OTP is 111111.",
            "metadata": {"user_id": "u-42", "source": "mobile"},
        },
        headers=HEADERS,
    )
    assert r.status_code == 200
    assert r.json()["metadata"] == {"user_id": "u-42", "source": "mobile"}


# ── Batch parse ───────────────────────────────────────────────────────────────

async def test_batch_parse_returns_results_in_order(client):
    messages = [
        {
            "sms_text": (
                "Payment made for GHS 35.00 to ERNESTINA ANDOH. "
                "Current Balance: GHS 1,037.64. Available Balance: GHS 1,037.64. "
                "Reference: 1. Transaction ID: 76289975115. "
                "Fee charged: GHS 0.00 TAX charged: GHS 0.00."
            ),
            "sender_id": "MobileMoney",
        },
        {"sms_text": "Your OTP is 482910."},
    ]
    r = await client.post(
        "/v1/parse/batch", json={"messages": messages}, headers=HEADERS
    )
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["results"]) == 2
    assert body["results"][0]["telco"] == "mtn"
    assert body["results"][1]["telco"] == "unknown"
    assert "processing_time_ms" in body


async def test_batch_empty_list_returns_422(client):
    r = await client.post(
        "/v1/parse/batch", json={"messages": []}, headers=HEADERS
    )
    assert r.status_code == 422


async def test_batch_over_100_returns_422(client):
    messages = [{"sms_text": "hi"} for _ in range(101)]
    r = await client.post(
        "/v1/parse/batch", json={"messages": messages}, headers=HEADERS
    )
    assert r.status_code == 422


# ── Sandbox ───────────────────────────────────────────────────────────────────

async def test_sandbox_key_is_accepted(client):
    r = await client.post(
        "/v1/parse",
        json={"sms_text": "test"},
        headers={"X-API-Key": SANDBOX_KEY},
    )
    # sandbox key is valid — should get 200, not 401
    assert r.status_code == 200
