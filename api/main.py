"""
MomoParse API — FastAPI application factory.

Start locally:
    uvicorn api.main:app --reload

Or via the Makefile:
    make dev
"""
from __future__ import annotations

import logging
import os
import time

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from api.logging_config import setup_logging
from api.routes import health, parse, enrich, report, jobs, demo

setup_logging()
logger = logging.getLogger("api")

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
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
            "documentation_url": "https://docs.momoparse.com/errors",
        },
    )


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - t0) * 1000, 2)
    logger.info(
        "%s %s → %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Database (creates tables on first startup) ───────────────────────────────

@app.on_event("startup")
def _startup_init_db():
    from db.engine import init_db

    init_db()


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix="/v1")
app.include_router(parse.router, prefix="/v1")
app.include_router(enrich.router, prefix="/v1")
app.include_router(report.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")
app.include_router(demo.router)


# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {"message": "MomoParse API v0.1.0 — see /docs"}
