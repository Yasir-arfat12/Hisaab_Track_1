from datetime import UTC, date, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.job import Job
from app.models.promise import Promise
from app.models.user import User
from app.schemas.common import ok
from app.schemas.finance import CreditUploadData
from app.services import credit_service
from app.services.verification_service import verify_fulfillment
from app.utils.exceptions import AppError, ErrorCode

router = APIRouter(prefix="/credits", tags=["Credits"])

MAX_CSV_BYTES = 10 * 1024 * 1024


async def _verify_open_promises_background(user_id: UUID, job_id: UUID, inserted: int) -> None:
    async with database.async_session_factory() as db:
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if job is None:
            return
        job.status = "running"
        job.progress = 50
        await db.commit()

        open_ids = (
            await db.execute(
                select(Promise.id).where(
                    Promise.user_id == user_id,
                    Promise.status.in_(["pending", "overdue"]),
                )
            )
        ).scalars().all()
        matched = 0
        for pid in open_ids:
            res = await verify_fulfillment(db, user_id, pid)
            if res.new_status == "kept":
                matched += 1

        job.status = "done"
        job.progress = 100
        job.result_json = {"credits_inserted": inserted, "promises_matched": matched}
        await db.commit()


@router.post("/upload")
async def upload_credits(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    bank_name: Annotated[str, Form(min_length=1, max_length=50)],
    account_last4: Annotated[str | None, Form(pattern=r"^[0-9]{4}$")] = None,
) -> dict:
    """Upload a bank credit CSV file, validate columns, ingest credits, and enqueue verification."""
    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_CSV_BYTES:
        raise AppError(
            code=ErrorCode.CREDIT_UPLOAD_FAILED,
            message="CSV file exceeds maximum size of 10 MB",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    parsed_rows = credit_service.parse_and_validate_csv(raw_bytes)
    inserted = await credit_service.insert_csv_credits(
        db,
        current_user.id,
        parsed_rows,
        bank_name=bank_name,
        account_last4=account_last4,
    )

    now = datetime.now(UTC)
    job = Job(
        id=uuid4(),
        user_id=current_user.id,
        type="csv_ingest",
        status="pending",
        progress=10,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()

    background_tasks.add_task(_verify_open_promises_background, current_user.id, job.id, inserted)

    return ok(
        CreditUploadData(
            job_id=job.id,
            rows_detected=len(parsed_rows),
            status="queued",
        ).model_dump(mode="json")
    )


@router.get("")
async def list_credits(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    matched: Annotated[bool | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> dict:
    """List bank credits for the authenticated user."""
    data = await credit_service.list_credits(
        db,
        current_user.id,
        matched=matched,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor=cursor,
    )
    return ok(data.model_dump(mode="json"))
