from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_user_status", "user_id", "status"),
        Index(
            "ix_jobs_idempotency_key",
            "idempotency_key",
            unique=True,
            sqlite_where=text("idempotency_key IS NOT NULL"),
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_jobs_user_type_created", "user_id", "type", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        Enum(
            "gmail_sync",
            "csv_ingest",
            "extraction",
            "dossier_generation",
            name="job_type",
            native_enum=False,
        ),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "running", "done", "failed", name="job_status", native_enum=False),
        nullable=False,
        default="pending",
    )
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
