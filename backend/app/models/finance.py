from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class BankCredit(Base):
    __tablename__ = "bank_credits"
    __table_args__ = (
        Index("ix_bank_credits_user_credited", "user_id", "credited_at"),
        Index("ix_bank_credits_user_amount", "user_id", "amount_paise"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(
        Enum("email", "csv", name="credit_source", native_enum=False),
        nullable=False,
    )
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)
    credited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    credit_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class VerificationMatch(Base):
    __tablename__ = "verification_matches"
    __table_args__ = (
        UniqueConstraint("promise_id", "credit_id", name="uq_verification_promise_credit"),
        Index("ix_verification_promise", "promise_id"),
        Index("ix_verification_credit", "credit_id"),
        Index("ix_verification_promise_ambiguous", "promise_id", "is_ambiguous"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    promise_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("promises.id", ondelete="CASCADE"), nullable=False
    )
    credit_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bank_credits.id", ondelete="CASCADE"), nullable=False
    )
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    matched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
