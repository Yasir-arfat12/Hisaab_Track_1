from datetime import UTC, datetime
from typing import Annotated, Literal, cast
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import database
from app.auth.dependencies import get_current_user
from app.auth.oauth import build_google_auth_url, create_oauth_state, revoke_google_token
from app.config import settings
from app.database import get_db
from app.models.email import Email
from app.models.job import Job
from app.models.user import GmailSyncState, OAuthToken, User
from app.schemas.common import ok
from app.schemas.job import (
    GmailDisconnectData,
    GmailStatusData,
    GmailSyncEnqueuedData,
    GmailSyncRequest,
)
from app.services.gmail_service import sync_gmail_for_user
from app.utils.encryption import decrypt_token
from app.utils.exceptions import AppError, ErrorCode

router = APIRouter(prefix="/gmail", tags=["Gmail"])


async def _run_sync_background(user_id: UUID, job_id: UUID, full_resync: bool) -> None:
    async with database.async_session_factory() as db:
        job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
        if job is None:
            return
        try:
            await sync_gmail_for_user(db, user_id, job, full_resync=full_resync)
        except (AppError, httpx.HTTPError):
            return


@router.post("/connect")
async def gmail_connect(
    response: Response,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Start Gmail OAuth flow for gmail.readonly scope."""
    state = create_oauth_state()
    redirect_url = build_google_auth_url(state)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return ok({"redirect_url": redirect_url})


@router.post("/disconnect")
async def gmail_disconnect(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Revoke Gmail token and purge raw email records for this user."""
    tokens = (
        await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == current_user.id,
                OAuthToken.provider == "google",
            )
        )
    ).scalars().all()
    for tok in tokens:
        await revoke_google_token(decrypt_token(tok.refresh_token_enc or tok.access_token_enc))

    await db.execute(delete(OAuthToken).where(OAuthToken.user_id == current_user.id))
    await db.execute(delete(GmailSyncState).where(GmailSyncState.user_id == current_user.id))
    email_count = int(
        (
            await db.execute(
                select(func.count(Email.id)).where(Email.user_id == current_user.id)
            )
        ).scalar_one()
    )
    await db.execute(delete(Email).where(Email.user_id == current_user.id))
    await db.commit()

    return ok(
        GmailDisconnectData(disconnected=True, emails_purged=email_count).model_dump(mode="json")
    )


@router.post("/sync")
async def gmail_sync(
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: GmailSyncRequest | None = None,
) -> dict:
    """Enqueue an idempotent background Gmail sync job."""
    tok = (
        await db.execute(
            select(OAuthToken.id).where(
                OAuthToken.user_id == current_user.id,
                OAuthToken.provider == "google",
            )
        )
    ).scalar_one_or_none()
    if tok is None:
        raise AppError(
            code=ErrorCode.GMAIL_AUTH_EXPIRED,
            message="Gmail is not connected or token expired",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    active_job = (
        await db.execute(
            select(Job).where(
                Job.user_id == current_user.id,
                Job.type == "gmail_sync",
                Job.status.in_(["pending", "running"]),
            )
        )
    ).scalar_one_or_none()
    if active_job is not None:
        raise AppError(
            code=ErrorCode.SYNC_IN_PROGRESS,
            message="A Gmail sync is already in progress",
            status_code=status.HTTP_409_CONFLICT,
            details={"job_id": str(active_job.id)},
        )

    now = datetime.now(UTC)
    job = Job(
        id=uuid4(),
        user_id=current_user.id,
        type="gmail_sync",
        status="pending",
        progress=0,
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.commit()

    full_resync = body.full_resync if body is not None else False
    background_tasks.add_task(_run_sync_background, current_user.id, job.id, full_resync)

    return ok(
        GmailSyncEnqueuedData(
            job_id=job.id,
            status="queued",
            enqueued_at=now,
        ).model_dump(mode="json")
    )


@router.get("/status")
async def gmail_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return current Gmail connection and sync status."""
    tok = (
        await db.execute(
            select(OAuthToken.id).where(
                OAuthToken.user_id == current_user.id,
                OAuthToken.provider == "google",
            )
        )
    ).scalar_one_or_none()
    connected = tok is not None

    sync_state = (
        await db.execute(
            select(GmailSyncState).where(GmailSyncState.user_id == current_user.id)
        )
    ).scalar_one_or_none()

    active_job = (
        await db.execute(
            select(Job).where(
                Job.user_id == current_user.id,
                Job.type == "gmail_sync",
                Job.status.in_(["pending", "running"]),
            )
        )
    ).scalar_one_or_none()

    emails_processed = int(
        (
            await db.execute(
                select(func.count(Email.id)).where(Email.user_id == current_user.id)
            )
        ).scalar_one()
    )

    sync_status: Literal["idle", "queued", "running"] = "idle"
    if active_job is not None:
        sync_status = "queued" if active_job.status == "pending" else "running"

    last_synced = (
        sync_state.last_synced_at.replace(tzinfo=UTC)
        if sync_state and sync_state.last_synced_at and sync_state.last_synced_at.tzinfo is None
        else (sync_state.last_synced_at if sync_state else None)
    )

    return ok(
        GmailStatusData(
            connected=connected,
            email=current_user.email if connected else None,
            last_synced_at=last_synced,
            sync_status=cast(Literal["idle", "queued", "running"], sync_status),
            active_job_id=active_job.id if active_job else None,
            emails_processed=emails_processed,
        ).model_dump(mode="json")
    )
