from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DemoScenario = Literal["refund_arrives", "refund_delayed", "fake_promise", "duplicate_charge"]


class DemoSimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: DemoScenario
    promise_id: UUID | None = None


class DemoSimulateResultData(BaseModel):
    scenario: DemoScenario
    affected_promise_id: UUID
    description: str
    simulated_at: datetime
