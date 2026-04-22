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
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
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

# ── Lifespan (runs on startup / shutdown) ─────────────────────────────────────

@asynccontextmanager
async def _lifespan(app: FastAPI):
    from db.engine import init_db

    init_db()
    yield


# ── App ───────────────────────────────────────────────────────────────────────

_SWAGGER_CSS = """
    body { background: #fafafa; }
    .swagger-ui .topbar { display: none; }
    .swagger-ui .info hgroup.main a { display: none; }
    .swagger-ui,
    .swagger-ui .info .title,
    .swagger-ui .opblock-tag,
    .swagger-ui .opblock .opblock-summary-description,
    .swagger-ui .opblock .opblock-summary-operation-id,
    .swagger-ui .opblock-description-wrapper p,
    .swagger-ui .response-col_description__inner p,
    .swagger-ui .parameter__name,
    .swagger-ui table thead tr th,
    .swagger-ui .model-title,
    .swagger-ui .model { font-family: 'Inter', -apple-system, sans-serif !important; }
    .swagger-ui .info .title { color: #111; font-weight: 700; }
    .swagger-ui .info .description p { color: #444; }
    .swagger-ui .scheme-container { background: #fafafa; border-bottom: 1px solid #e5e5e5; box-shadow: none; }
    .swagger-ui .opblock.opblock-get .opblock-summary-method { background: #0d9488; }
    .swagger-ui .opblock.opblock-post .opblock-summary-method { background: #111; }
    .swagger-ui .opblock.opblock-get { border-color: #0d9488; background: rgba(13,148,136,0.03); }
    .swagger-ui .opblock.opblock-post { border-color: #111; background: rgba(0,0,0,0.02); }
    .swagger-ui .btn.execute { background: #111; border-color: #111; }
    .swagger-ui .btn.execute:hover { background: #333; }
    .swagger-ui .btn.authorize { color: #0d9488; border-color: #0d9488; }
    .swagger-ui .btn.authorize svg { fill: #0d9488; }
    .swagger-ui .response-col_status .response-undocumented { color: #0d9488; }
"""

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
    version="0.2.0",
    contact={"name": "MomoParse", "email": "hello@momoparse.com"},
    license_info={"name": "Proprietary"},
    docs_url=None,
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=_lifespan,
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
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(health.router, prefix="/v1")
app.include_router(parse.router, prefix="/v1")
app.include_router(enrich.router, prefix="/v1")
app.include_router(report.router, prefix="/v1")
app.include_router(jobs.router, prefix="/v1")
app.include_router(demo.router)


# ── Custom Swagger UI ─────────────────────────────────────────────────────────

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui() -> HTMLResponse:
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} — docs",
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "docExpansion": "list",
            "filter": True,
            "syntaxHighlight.theme": "monokai",
        },
    )
    # Inject Inter font + custom CSS before </head>
    inject = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">'
        f"<style>{_SWAGGER_CSS}</style>"
    )
    styled = html.body.decode().replace("</head>", f"{inject}</head>")
    return HTMLResponse(styled)


# ── Root redirect ─────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {"message": "MomoParse API v0.2.0 — see /docs"}
