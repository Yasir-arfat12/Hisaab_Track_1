from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.schemas.escalation import EscalationDraftRequest
from app.services import escalation_service

router = APIRouter(prefix="/escalation", tags=["Escalation"])


@router.get("/{promise_id}/next-step")
async def get_next_step(
    promise_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return deterministic next escalation rung and IST deadline."""
    data = await escalation_service.get_next_escalation_step(
        db, current_user.id, promise_id
    )
    return ok(data.model_dump(mode="json"))


@router.post("/{promise_id}/draft")
async def generate_draft(
    promise_id: UUID,
    body: EscalationDraftRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Generate escalation draft message via LLM with deterministic template fallback."""
    data = await escalation_service.generate_escalation_draft(
        db, current_user.id, promise_id, body
    )
    return ok(data.model_dump(mode="json"))
