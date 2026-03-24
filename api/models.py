"""
Pydantic request / response models for the MomoParse API.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ── Request models ────────────────────────────────────────────────────────────

class ParseRequest(BaseModel):
    sms_text: str = Field(..., min_length=1, description="Raw MoMo SMS text to parse")
    sender_id: Optional[str] = Field(
        None,
        max_length=50,
        description="SMS sender ID (e.g. 'MobileMoney', 'T-CASH'). Improves telco detection.",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Optional caller-supplied metadata echoed back in the response.",
    )

    @field_validator("sms_text")
    @classmethod
    def sms_text_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sms_text must not be blank")
        return v


class BatchParseRequest(BaseModel):
    messages: list[ParseRequest] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Array of SMS messages to parse (max 100 per request).",
    )


# ── Response models ───────────────────────────────────────────────────────────

class CounterpartyModel(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


class ParseResponse(BaseModel):
    request_id: str = Field(description="Unique ID for this parse request.")
    api_version: str = Field(default="v1")
    processing_time_ms: float = Field(description="End-to-end processing time in milliseconds.")

    # Core parse fields
    telco: str
    tx_type: str
    template_id: Optional[str] = None
    confidence: float

    amount: Optional[float] = None
    currency: str = "GHS"
    balance: Optional[float] = None
    fee: Optional[float] = None

    counterparty: CounterpartyModel
    tx_id: Optional[str] = None
    reference: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None

    # Categorization (Week 5)
    category: Optional[str] = Field(None, description="Financial category slug (e.g. 'personal_transfer_sent')")
    category_label: Optional[str] = Field(None, description="Human-readable category label")
    category_confidence: Optional[float] = Field(None, description="Categorization confidence in [0, 1]")

    metadata: Optional[dict[str, Any]] = None


class BatchParseResponse(BaseModel):
    request_id: str
    api_version: str = "v1"
    processing_time_ms: float
    count: int
    results: list[ParseResponse]


# ── Enrichment models (Week 6) ────────────────────────────────────────────────

class EnrichRequest(BaseModel):
    messages: list[ParseRequest] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Array of SMS messages to enrich (max 1,000 per request).",
    )
    webhook_url: Optional[str] = Field(
        None,
        description="If provided and message count >= 500, results are POSTed here when ready.",
    )


class CategoryBreakdown(BaseModel):
    amount: float
    count: int
    percentage: float


class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    days_covered: int = 0


class EnrichSummary(BaseModel):
    total_income: float
    total_expenses: float
    net_cash_flow: float
    transaction_count: int
    category_breakdown: dict[str, CategoryBreakdown]
    transaction_frequency_per_day: float
    unique_counterparties: int
    date_range: DateRange


class EnrichResponse(BaseModel):
    request_id: str
    api_version: str = "v1"
    processing_time_ms: Optional[float] = None
    job_id: Optional[str] = Field(None, description="Populated when request is processed asynchronously.")
    status: str = "complete"
    summary: Optional[EnrichSummary] = None


class CounterpartySummary(BaseModel):
    identifier: str
    total_amount: float
    transaction_count: int


class RiskSignal(BaseModel):
    signal: str
    description: str
    severity: str  # "low" | "medium" | "high"


class FinancialIndexes(BaseModel):
    savings_rate: float = Field(description="(Income - Expenses) / Income × 100. Standard personal finance metric.")
    transaction_velocity: float = Field(description="Transactions per day. Proxy for economic activity.")
    income_stability_index: float = Field(
        description="Coefficient of variation of monthly income. 0 = perfectly stable, >1 = highly volatile."
    )
    counterparty_concentration_hhi: float = Field(
        description="Herfindahl-Hirschman Index of transaction partners. 0 = diversified, 1 = single counterparty."
    )
    expense_volatility: float = Field(
        description="Normalized std deviation of monthly spending. Lower = more predictable."
    )
    composite_health_score: int = Field(description="Weighted composite of all indexes, 0–100.")
    data_points: Optional[dict] = Field(None, description="Months, transactions, and counterparties used.")


class ProfileResponse(BaseModel):
    request_id: str
    api_version: str = "v1"
    processing_time_ms: Optional[float] = None
    job_id: Optional[str] = None
    status: str = "complete"
    avg_monthly_income: Optional[float] = None
    income_consistency_cv: Optional[float] = Field(
        None, description="Coefficient of variation of monthly income. Lower = more consistent."
    )
    expense_ratio: Optional[float] = None
    top_counterparties: list[CounterpartySummary] = []
    business_activity_score: Optional[int] = Field(None, description="0–100 score of business activity.")
    revenue_trend: Optional[str] = Field(None, description="growing | stable | declining")
    risk_signals: list[RiskSignal] = []
    months_of_data: int = 0
    financial_indexes: Optional[FinancialIndexes] = Field(
        None, description="Formalized financial indexes grounded in established methodology."
    )
    summary: Optional[EnrichSummary] = None


# ── Monthly report models (Week 8) ───────────────────────────────────────────


class MonthBreakdown(BaseModel):
    month: str = Field(description="YYYY-MM")
    income: float
    expenses: float
    net_savings: float
    savings_rate: float = Field(description="Percentage of income saved")
    transaction_count: int


class Insight(BaseModel):
    type: str = Field(description="top_spending | spending_trend | fee_alert | airtime_alert")
    title: str
    detail: str


class SavingsAnalysis(BaseModel):
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float = Field(description="Overall savings rate as percentage")


class Recommendation(BaseModel):
    priority: str = Field(description="high | medium | info")
    title: str
    detail: str


class ReportResponse(BaseModel):
    request_id: str
    api_version: str = "v1"
    processing_time_ms: Optional[float] = None
    job_id: Optional[str] = Field(None, description="Populated when request is processed asynchronously.")
    status: str = "complete"
    months: list[MonthBreakdown] = []
    insights: list[Insight] = []
    savings_analysis: Optional[SavingsAnalysis] = None
    recommendations: list[Recommendation] = []
    financial_health_score: Optional[int] = Field(None, description="0–100 composite score from formalized indexes")
    financial_indexes: Optional[FinancialIndexes] = Field(
        None, description="Formalized financial indexes grounded in established methodology."
    )
    summary: Optional[EnrichSummary] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    message_count: int
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ── Error models ──────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    error_code: str
    message: str
    documentation_url: str = "https://docs.momoparse.com/errors"


# ── Health model ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    uptime_seconds: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def new_request_id() -> str:
    return str(uuid.uuid4())


_SERVER_START = time.monotonic()


def uptime() -> float:
    return round(time.monotonic() - _SERVER_START, 2)
