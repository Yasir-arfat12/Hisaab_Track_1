from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_user_processed", "user_id", "processed_at"),
        Index("ix_emails_body_hash", "body_hash"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    gmail_message_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sender: Mapped[str] = mapped_column(String(500), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    body_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
