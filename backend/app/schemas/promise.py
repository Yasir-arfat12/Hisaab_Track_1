from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PromiseStatus = Literal["pending", "kept", "overdue", "needs_review", "dismissed"]
PromiseCategory = Literal["refund", "delivery_credit", "insurance", "ticket", "other"]
ExtractionMethod = Literal["llm", "deterministic"]
TimelineEventType = Literal[
    "promise_extracted",
    "credit_matched",
    "overdue_detected",
    "escalation_advanced",
    "user_note_added",
    "status_changed",
    "verification_run",
]


class PromiseSummary(BaseModel):
    promise_id: UUID
    merchant_name: str
    merchant_id: UUID
    category: str | None
    amount_paise: int | None
    status: PromiseStatus
    due_date: date | None
    created_at: datetime


class TimelineEvent(BaseModel):
    event_id: str
    type: TimelineEventType
    description: str
    occurred_at: datetime
    metadata: dict[str, Any] | None = None


class PromiseDetail(PromiseSummary):
    received_amount_paise: int | None = None
    source_email_id: str | None = None
    source_email_subject: str | None = None
    user_note: str | None = None
    escalation_rung: int | None = Field(default=None, ge=1, le=4)
    exact_quote: str
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_method: ExtractionMethod
    needs_review_reason: str | None = None
    updated_at: datetime
    timeline: list[TimelineEvent]


class PromiseListData(BaseModel):
    items: list[PromiseSummary]
    next_cursor: str | None
    prev_cursor: str | None
    limit: int


class PromisePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["dismissed"] | None = None
    user_note: str | None = Field(default=None, max_length=2000)
