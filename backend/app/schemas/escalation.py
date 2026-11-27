from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EscalationNextStepData(BaseModel):
    promise_id: UUID
    current_rung: int | None = None
    next_rung: int = Field(ge=1, le=4)
    rung_name: str
    rung_description: str
    deadline_date: date
    days_until_deadline: int
    legal_forum: str | None = None


class EscalationDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rung: int = Field(ge=1, le=4)
    tone: Literal["firm", "polite"] = "firm"
    include_legal_references: bool = False


class EscalationDraftData(BaseModel):
    draft_text: str
    rung: int = Field(ge=1, le=4)
    not_legal_advice_notice: str
    generated_at: datetime
    model_used: str


class DossierGenerateData(BaseModel):
    job_id: UUID
    status: Literal["queued"]
    enqueued_at: datetime
