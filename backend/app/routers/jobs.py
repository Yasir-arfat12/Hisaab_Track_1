from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.common import ok
from app.schemas.job import JobData
from app.utils.exceptions import AppError, ErrorCode

router = APIRouter(prefix="/jobs", tags=["Jobs"])

_STATUS_MAP: dict[str, Literal["queued", "running", "completed", "failed"]] = {
    "pending": "queued",
    "running": "running",
    "done": "completed",
    "failed": "failed",
}
_TYPE_MAP: dict[str, Literal["gmail_sync", "credit_upload", "dossier_generation"]] = {
    "gmail_sync": "gmail_sync",
    "csv_ingest": "credit_upload",
    "dossier_generation": "dossier_generation",
}


@router.get("/{job_id}")
async def get_job(
    job_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return status, progress, and result of a background job owned by the user."""
    job = (
        await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    ).scalar_one_or_none()
    if job is None:
        raise AppError(
            code=ErrorCode.JOB_NOT_FOUND,
            message="No job found with the given ID",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"job_id": str(job_id)},
        )

    api_status = _STATUS_MAP.get(job.status, "queued")
    api_type = _TYPE_MAP.get(job.type, "gmail_sync")
    completed_at = job.updated_at if api_status in ("completed", "failed") else None

    return ok(
        JobData(
            job_id=job.id,
            type=api_type,
            status=api_status,
            progress_pct=job.progress,
            created_at=job.created_at,
            completed_at=completed_at,
            result=job.result_json,
            error_message=job.error_msg,
        ).model_dump(mode="json")
    )
