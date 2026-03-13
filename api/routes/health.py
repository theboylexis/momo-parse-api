"""GET /v1/health — liveness probe."""
from fastapi import APIRouter
from api.models import HealthResponse, uptime

router = APIRouter()

VERSION = "0.1.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["meta"],
)
def health():
    """Returns server status and uptime. No authentication required."""
    return HealthResponse(version=VERSION, uptime_seconds=uptime())
