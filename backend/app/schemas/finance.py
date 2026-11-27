from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

PromiseStatus = Literal["pending", "kept", "overdue", "needs_review", "dismissed"]


class BankCreditItem(BaseModel):
    credit_id: UUID
    date: date
    description: str
    amount_paise: int
    reference_number: str | None = None
    matched_promise_id: UUID | None = None
    bank_name: str


class BankCreditListData(BaseModel):
    items: list[BankCreditItem]
    next_cursor: str | None
    prev_cursor: str | None
    limit: int


class CreditUploadData(BaseModel):
    job_id: UUID
    rows_detected: int
    status: Literal["queued"]


class VerifyResultData(BaseModel):
    promise_id: UUID
    previous_status: PromiseStatus
    new_status: PromiseStatus
    matched_credit_id: UUID | None = None
    amount_paise_expected: int | None
    amount_paise_received: int | None = None
    verified_at: datetime
