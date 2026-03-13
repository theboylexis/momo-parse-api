"""
Tests for Week 6 enrichment endpoints.

Covers:
- POST /v1/enrich — sync (< 500 SMS) and async (>= 500 SMS)
- POST /v1/profile — sync financial profile
- GET /v1/jobs/{job_id} — async job polling
- Analytics: income/expense classification, category breakdown, risk signals
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

BASE = "http://test"
HEADERS = {"X-API-Key": "sk-sandbox-momoparse"}

# Real SMS from our corpus that the parser can handle
_MTN_TRANSFER_SENT = (
    "Payment made for GHS 20.00 to LOUISA BOATENG. "
    "Current Balance: GHS 500.00. Reference: veggies. "
    "Transaction ID: 76664093335. Fee charged: GHS 0.00"
)
_MTN_TRANSFER_RECEIVED = (
    "Payment received for GHS 50.00 from DAVID BOATENG "
    "Current Balance: GHS 550.00. Reference: salary. "
    "Transaction ID: 76712833868. TRANSACTION FEE: 0.00"
)


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as c:
        yield c


# ── /v1/enrich (sync) ────────────────────────────────────────────────────────

async def test_enrich_returns_summary(client):
    resp = await client.post("/v1/enrich", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert "summary" in data
    summary = data["summary"]
    assert "total_income" in summary
    assert "total_expenses" in summary
    assert "net_cash_flow" in summary
    assert "category_breakdown" in summary
    assert "transaction_count" in summary
    assert summary["transaction_count"] == 2


async def test_enrich_requires_auth(client):
    resp = await client.post("/v1/enrich", json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 401


async def test_enrich_rejects_empty_messages(client):
    resp = await client.post("/v1/enrich", headers=HEADERS, json={"messages": []})
    assert resp.status_code == 422


async def test_enrich_category_breakdown_present(client):
    resp = await client.post("/v1/enrich", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    breakdown = resp.json()["summary"]["category_breakdown"]
    assert isinstance(breakdown, dict)
    # Each entry has amount, count, percentage
    for cat, vals in breakdown.items():
        assert "amount" in vals
        assert "count" in vals
        assert "percentage" in vals


async def test_enrich_date_range_present(client):
    resp = await client.post("/v1/enrich", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    date_range = resp.json()["summary"]["date_range"]
    assert "days_covered" in date_range


async def test_enrich_unique_counterparties(client):
    resp = await client.post("/v1/enrich", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    assert resp.json()["summary"]["unique_counterparties"] >= 0


# ── /v1/enrich (async) ───────────────────────────────────────────────────────

async def test_enrich_large_batch_returns_job_id(client):
    messages = [{"sms_text": _MTN_TRANSFER_SENT}] * 500
    resp = await client.post("/v1/enrich", headers=HEADERS, json={"messages": messages})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert "job_id" in data
    assert data["job_id"] is not None


# ── GET /v1/jobs/{job_id} ────────────────────────────────────────────────────

async def test_job_poll_returns_status(client):
    # Queue a job first
    messages = [{"sms_text": _MTN_TRANSFER_SENT}] * 500
    enrich_resp = await client.post("/v1/enrich", headers=HEADERS, json={"messages": messages})
    job_id = enrich_resp.json()["job_id"]

    # Poll it
    poll_resp = await client.get(f"/v1/jobs/{job_id}")
    assert poll_resp.status_code == 200
    job = poll_resp.json()
    assert job["job_id"] == job_id
    assert job["status"] in ("pending", "processing", "complete", "failed")
    assert job["message_count"] == 500


async def test_job_not_found(client):
    resp = await client.get("/v1/jobs/nonexistent-job-id")
    assert resp.status_code == 404


# ── /v1/profile ──────────────────────────────────────────────────────────────

async def test_profile_returns_all_fields(client):
    resp = await client.post("/v1/profile", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert "avg_monthly_income" in data
    assert "income_consistency_cv" in data
    assert "expense_ratio" in data
    assert "business_activity_score" in data
    assert "revenue_trend" in data
    assert "risk_signals" in data
    assert "top_counterparties" in data
    assert "summary" in data


async def test_profile_business_score_in_range(client):
    resp = await client.post("/v1/profile", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    score = resp.json()["business_activity_score"]
    assert 0 <= score <= 100


async def test_profile_revenue_trend_valid(client):
    resp = await client.post("/v1/profile", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    trend = resp.json()["revenue_trend"]
    assert trend in ("growing", "stable", "declining")


async def test_profile_risk_signals_are_list(client):
    resp = await client.post("/v1/profile", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    signals = resp.json()["risk_signals"]
    assert isinstance(signals, list)


async def test_profile_large_batch_returns_job_id(client):
    messages = [{"sms_text": _MTN_TRANSFER_SENT}] * 500
    resp = await client.post("/v1/profile", headers=HEADERS, json={"messages": messages})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"] is not None


# ── Analytics unit tests ──────────────────────────────────────────────────────

def test_compute_summary_income_expense_split():
    from enricher.analytics import compute_summary
    txs = [
        {"tx_type": "transfer_received", "amount": 500.0, "category": "sales_revenue",
         "counterparty_name": "A", "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 100.0, "category": "supplier_payment",
         "counterparty_name": "B", "counterparty_phone": None, "date": "2026-01-15", "fee": 0.5},
    ]
    result = compute_summary(txs)
    assert result["total_income"] == 500.0
    assert result["total_expenses"] == 100.0
    assert result["net_cash_flow"] == 400.0
    assert result["transaction_count"] == 2


def test_compute_summary_date_range():
    from enricher.analytics import compute_summary
    txs = [
        {"tx_type": "transfer_received", "amount": 100.0, "category": "personal_transfer_received",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-01", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 50.0, "category": "personal_transfer_sent",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-03-01", "fee": 0.0},
    ]
    result = compute_summary(txs)
    assert result["date_range"]["start"] == "2026-01-01"
    assert result["date_range"]["end"] == "2026-03-01"
    assert result["date_range"]["days_covered"] == 59


def test_compute_profile_expense_ratio():
    from enricher.analytics import compute_profile
    txs = [
        {"tx_type": "transfer_received", "amount": 1000.0, "category": "sales_revenue",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 400.0, "category": "supplier_payment",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-20", "fee": 0.0},
    ]
    result = compute_profile(txs)
    assert abs(result["expense_ratio"] - 0.4) < 0.01
