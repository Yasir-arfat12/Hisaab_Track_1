from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Merchant(Base):
    __tablename__ = "merchants"
    __table_args__ = (Index("ix_merchants_domain", "domain"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    promises: Mapped[list["Promise"]] = relationship(back_populates="merchant")


class Promise(Base):
    __tablename__ = "promises"
    __table_args__ = (
        Index("ix_promises_user_status", "user_id", "status"),
        Index("ix_promises_user_merchant", "user_id", "merchant_id"),
        Index("ix_promises_due_date", "due_date"),
        Index("ix_promises_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    email_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("emails.id", ondelete="SET NULL"), nullable=True
    )
    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("merchants.id"), nullable=False
    )
    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount_paise: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    exact_quote: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "pending",
            "kept",
            "overdue",
            "needs_review",
            "dismissed",
            name="promise_status",
            native_enum=False,
        ),
        nullable=False,
        default="pending",
    )
    extraction_method: Mapped[str] = mapped_column(
        Enum("llm", "deterministic", name="extraction_method", native_enum=False),
        nullable=False,
    )
    needs_review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="promises")
