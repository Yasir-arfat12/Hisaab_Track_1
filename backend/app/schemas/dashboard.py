from datetime import datetime

from pydantic import BaseModel


class DashboardCounts(BaseModel):
    total: int
    pending: int
    kept: int
    overdue: int
    needs_review: int
    dismissed: int


class DashboardSummaryData(BaseModel):
    total_owed_paise: int
    total_overdue_paise: int
    total_kept_paise: int
    counts: DashboardCounts
    computed_at: datetime
