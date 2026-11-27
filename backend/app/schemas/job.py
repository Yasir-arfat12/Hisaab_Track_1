from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class JobData(BaseModel):
    job_id: UUID
    type: Literal["gmail_sync", "credit_upload", "dossier_generation"]
    status: Literal["queued", "running", "completed", "failed"]
    progress_pct: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None


class GmailSyncRequest(BaseModel):
    full_resync: bool = False


class GmailSyncEnqueuedData(BaseModel):
    job_id: UUID
    status: Literal["queued", "running"]
    enqueued_at: datetime


class GmailDisconnectData(BaseModel):
    disconnected: bool
    emails_purged: int


class GmailStatusData(BaseModel):
    connected: bool
    email: str | None = None
    last_synced_at: datetime | None = None
    sync_status: Literal["idle", "queued", "running"]
    active_job_id: UUID | None = None
    emails_processed: int
