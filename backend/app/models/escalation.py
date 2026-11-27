from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Index, SmallInteger, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class EscalationStep(Base):
    __tablename__ = "escalation_steps"
    __table_args__ = (
        Index("ix_escalation_promise", "promise_id"),
        Index("uq_escalation_promise_rung", "promise_id", "rung", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    promise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("promises.id", ondelete="CASCADE"), nullable=False
    )
    rung: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    deadline: Mapped[date] = mapped_column(Date, nullable=False)
    draft_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    notice_type: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
