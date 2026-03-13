"""
MomoParse API — FastAPI application factory.

Start locally:
    uvicorn api.main:app --reload

Or via the Makefile:
    make dev
"""
from __future__ import annotations

import os

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from api.routes import health, parse

# ── Sentry (error monitoring) ─────────────────────────────────────────────────
# Set SENTRY_DSN env var in production. No-op locally if the var is absent.

_dsn = os.getenv("SENTRY_DSN")
if _dsn:
    sentry_sdk.init(
        dsn=_dsn,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.1,   # 10% of requests traced for performance
        send_default_pii=False,
    )

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MomoParse API",
    summary="Transaction intelligence for Mobile Money SMS",
    description=(
        "MomoParse transforms raw MoMo SMS messages into structured, "
        "categorized financial data — the **Plaid Enrich** for mobile money markets.\n\n"
        "**Base URL:** `https://api.momoparse.com`\n\n"
        "**Authentication:** All endpoints (except `/v1/health`) require an "
        "`X-API-Key` header. Get your key at [momoparse.com](https://momoparse.com).\n\n"
        "**Sandbox key:** `sk-sandbox-momoparse` — free, no sign-up, 100 calls/day."
    ),
    version="0.1.0",
    contact={"name": "MomoParse", "email": "hello@momoparse.com"},
    license_info={"name": "Proprietary"},
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
            "documentation_url": "https://docs.momoparse.com/errors",
        },
    )


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix="/v1")
app.include_router(parse.router, prefix="/v1")


# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {"message": "MomoParse API v0.1.0 — see /docs"}
