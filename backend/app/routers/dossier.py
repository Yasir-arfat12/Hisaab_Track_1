from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.job import Job
from app.models.user import User
from app.schemas.common import ok
from app.schemas.escalation import DossierGenerateData
from app.services import dossier_service, promise_service

router = APIRouter(prefix="/dossier", tags=["Dossier"])


async def _generate_dossier_background(user_id: UUID, promise_id: UUID, job_id: UUID) -> None:
    async with database.async_session_factory() as db:
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if job is None:
            return
        job.status = "running"
        job.progress = 25
        await db.commit()

        path = await dossier_service.generate_and_save_dossier_pdf(db, user_id, promise_id)
        job.status = "done"
        job.progress = 100
        job.result_json = {"promise_id": str(promise_id), "file": path.name}
        await db.commit()


@router.post("/{promise_id}/generate")
async def generate_dossier(
    promise_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Enqueue PDF dossier generation job for a promise."""
    await promise_service.get_promise_detail(db, current_user.id, promise_id)

    now = datetime.now(UTC)
    job = Job(
        id=uuid4(),
        user_id=current_user.id,
        type="dossier_generation",
        status="pending",
        progress=0,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()

    background_tasks.add_task(
        _generate_dossier_background, current_user.id, promise_id, job.id
    )

    return ok(
        DossierGenerateData(
            job_id=job.id,
            status="queued",
            enqueued_at=now,
        ).model_dump(mode="json")
    )


@router.get("/{promise_id}/download")
async def download_dossier(
    promise_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Stream generated PDF dossier bytes."""
    pdf_bytes = await dossier_service.load_dossier_pdf_bytes(
        db, current_user.id, promise_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="hisaab-dossier-{promise_id}.pdf"'
        },
    )
