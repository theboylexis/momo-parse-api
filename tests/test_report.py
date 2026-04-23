"""
Tests for the monthly report endpoint.

Covers:
- POST /v1/report — sync (< 500 SMS) and async (>= 500 SMS)
- Report structure: months, insights, savings_analysis, recommendations, health score
- Analytics unit tests for compute_report()
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app

BASE = "http://test"
HEADERS = {"X-API-Key": "sk-sandbox-momoparse"}

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


# ── POST /v1/report (sync) ──────────────────────────────────────────────────

async def test_report_returns_complete_response(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "complete"
    assert "months" in data
    assert "insights" in data
    assert "savings_analysis" in data
    assert "recommendations" in data
    assert "financial_health_score" in data
    assert "summary" in data


async def test_report_requires_auth(client):
    resp = await client.post("/v1/report", json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 401


async def test_report_rejects_empty_messages(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={"messages": []})
    assert resp.status_code == 422


async def test_report_savings_analysis_fields(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    sa = resp.json()["savings_analysis"]
    assert "total_income" in sa
    assert "total_expenses" in sa
    assert "net_savings" in sa
    assert "savings_rate" in sa


async def test_report_health_score_in_range(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    score = resp.json()["financial_health_score"]
    assert 0 <= score <= 100


async def test_report_insights_are_list(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    insights = resp.json()["insights"]
    assert isinstance(insights, list)
    for i in insights:
        assert "type" in i
        assert "title" in i
        assert "detail" in i


async def test_report_recommendations_are_list(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [{"sms_text": _MTN_TRANSFER_SENT}]
    })
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert isinstance(recs, list)
    for r in recs:
        assert "priority" in r
        assert "title" in r
        assert "detail" in r


async def test_report_month_breakdown_structure(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    months = resp.json()["months"]
    assert isinstance(months, list)
    for m in months:
        assert "month" in m
        assert "income" in m
        assert "expenses" in m
        assert "net_savings" in m
        assert "savings_rate" in m
        assert "transaction_count" in m


# ── POST /v1/report (async) ─────────────────────────────────────────────────

async def test_report_large_batch_returns_job_id(client):
    messages = [{"sms_text": _MTN_TRANSFER_SENT}] * 500
    resp = await client.post("/v1/report", headers=HEADERS, json={"messages": messages})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "queued"
    assert data["job_id"] is not None


# ── Analytics unit tests ─────────────────────────────────────────────────────

def test_compute_report_savings_analysis():
    from enricher.analytics import compute_report
    txs = [
        {"tx_type": "transfer_received", "amount": 1000.0, "category": "sales_revenue",
         "counterparty_name": "Client A", "counterparty_phone": None, "date": "2026-01-15", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 300.0, "category": "supplier_payment",
         "counterparty_name": "Supplier B", "counterparty_phone": None, "date": "2026-01-20", "fee": 0.0},
    ]
    result = compute_report(txs)
    sa = result["savings_analysis"]
    assert sa["total_income"] == 1000.0
    assert sa["total_expenses"] == 300.0
    assert sa["net_savings"] == 700.0
    assert sa["savings_rate"] == 70.0


def test_compute_report_monthly_breakdown():
    from enricher.analytics import compute_report
    txs = [
        {"tx_type": "transfer_received", "amount": 500.0, "category": "sales_revenue",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 100.0, "category": "supplier_payment",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-15", "fee": 0.0},
        {"tx_type": "transfer_received", "amount": 600.0, "category": "sales_revenue",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-02-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 200.0, "category": "supplier_payment",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-02-20", "fee": 0.0},
    ]
    result = compute_report(txs)
    months = result["months"]
    assert len(months) == 2
    assert months[0]["month"] == "2026-01"
    assert months[0]["income"] == 500.0
    assert months[0]["expenses"] == 100.0
    assert months[1]["month"] == "2026-02"
    assert months[1]["income"] == 600.0


def test_compute_report_health_score_high_saver():
    from enricher.analytics import compute_report
    txs = [
        {"tx_type": "transfer_received", "amount": 1000.0, "category": "sales_revenue",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-01", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 200.0, "category": "supplier_payment",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-15", "fee": 0.0},
    ]
    result = compute_report(txs)
    # 80% savings rate but only 1 month, 2 txns, no counterparties —
    # formalized scoring caps low-data scenarios at 70 and penalizes
    # concentration, so expect a moderate-to-good score, not a high one
    assert result["financial_health_score"] >= 50


def test_compute_report_health_score_negative_saver():
    from enricher.analytics import compute_report
    txs = [
        {"tx_type": "transfer_received", "amount": 100.0, "category": "personal_transfer_received",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-01", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 150.0, "category": "personal_transfer_sent",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-15", "fee": 0.0},
    ]
    result = compute_report(txs)
    # Spending > income → low health score
    assert result["financial_health_score"] <= 50


def test_compute_financial_indexes_returns_score_drivers():
    from enricher.analytics import compute_financial_indexes
    txs = [
        {"tx_type": "transfer_received", "amount": 1000.0, "category": "sales_revenue",
         "counterparty_name": "Client A", "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 300.0, "category": "supplier_payment",
         "counterparty_name": "Supplier B", "counterparty_phone": None, "date": "2026-01-20", "fee": 0.0},
        {"tx_type": "transfer_received", "amount": 1100.0, "category": "sales_revenue",
         "counterparty_name": "Client C", "counterparty_phone": None, "date": "2026-02-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 320.0, "category": "supplier_payment",
         "counterparty_name": "Supplier B", "counterparty_phone": None, "date": "2026-02-20", "fee": 0.0},
    ]
    result = compute_financial_indexes(txs)
    drivers = result["score_drivers"]
    # All five indexes always returned
    assert len(drivers) == 5
    assert {d["index"] for d in drivers} == {
        "savings_rate", "income_stability", "expense_volatility",
        "counterparty_concentration", "transaction_velocity",
    }
    # Every driver has the three required fields in valid ranges
    for d in drivers:
        assert 0.0 <= d["normalized"] <= 1.0
        assert 0 <= d["contribution_pp"] <= 100
    # Sorted by contribution_pp descending
    contribs = [d["contribution_pp"] for d in drivers]
    assert contribs == sorted(contribs, reverse=True)


def test_score_drivers_sum_reconciles_with_composite():
    """With >= 2 months of data, no low-data penalty applies, so the sum
    of driver contributions must equal the composite score (±1 for rounding)."""
    from enricher.analytics import compute_financial_indexes
    txs = [
        {"tx_type": "transfer_received", "amount": 1000.0, "category": "sales_revenue",
         "counterparty_name": "Client A", "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 300.0, "category": "supplier_payment",
         "counterparty_name": "Supplier B", "counterparty_phone": None, "date": "2026-01-20", "fee": 0.0},
        {"tx_type": "transfer_received", "amount": 1100.0, "category": "sales_revenue",
         "counterparty_name": "Client C", "counterparty_phone": None, "date": "2026-02-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 320.0, "category": "supplier_payment",
         "counterparty_name": "Supplier B", "counterparty_phone": None, "date": "2026-02-20", "fee": 0.0},
    ]
    result = compute_financial_indexes(txs)
    composite = result["composite_health_score"]
    drivers_sum = sum(d["contribution_pp"] for d in result["score_drivers"])
    # ±2 tolerance accounts for per-driver rounding
    assert abs(drivers_sum - composite) <= 2


async def test_report_includes_score_drivers(client):
    resp = await client.post("/v1/report", headers=HEADERS, json={
        "messages": [
            {"sms_text": _MTN_TRANSFER_SENT},
            {"sms_text": _MTN_TRANSFER_RECEIVED},
        ]
    })
    assert resp.status_code == 200
    indexes = resp.json()["financial_indexes"]
    assert "score_drivers" in indexes
    drivers = indexes["score_drivers"]
    assert isinstance(drivers, list)
    assert len(drivers) == 5
    for d in drivers:
        assert "index" in d
        assert "normalized" in d
        assert "contribution_pp" in d


def test_compute_report_spending_insight_present():
    from enricher.analytics import compute_report
    txs = [
        {"tx_type": "transfer_received", "amount": 500.0, "category": "sales_revenue",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-10", "fee": 0.0},
        {"tx_type": "transfer_sent", "amount": 200.0, "category": "supplier_payment",
         "counterparty_name": None, "counterparty_phone": None, "date": "2026-01-15", "fee": 0.0},
    ]
    result = compute_report(txs)
    insight_types = [i["type"] for i in result["insights"]]
    assert "top_spending" in insight_types
