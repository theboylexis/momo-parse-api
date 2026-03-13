"""GET /v1/jobs/{job_id} — poll async job status."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from enricher import jobs as job_store
from api.models import JobStatusResponse

router = APIRouter()


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll async job status",
    tags=["enrich"],
    responses={
        404: {"description": "Job not found"},
    },
)
def get_job(job_id: str):
    """
    Poll the status of an async enrichment or profile job.

    - **pending** — queued, not yet started
    - **processing** — actively being processed
    - **complete** — result is available in the `result` field
    - **failed** — check the `error` field
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "JOB_NOT_FOUND", "message": f"No job with id {job_id!r}"},
        )
    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        created_at=job.created_at,
        completed_at=job.completed_at,
        message_count=job.message_count,
        result=job.result,
        error=job.error,
    )
