from uuid import UUID

from pydantic import BaseModel


class MerchantRecordData(BaseModel):
    merchant_id: UUID
    merchant_name: str
    total_promises: int
    kept_count: int
    overdue_count: int
    dismissed_count: int
    average_resolution_days: float | None = None
    keep_rate_pct: float
