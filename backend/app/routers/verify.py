from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.services.verification_service import verify_fulfillment

router = APIRouter(prefix="/verify", tags=["Verify"])


@router.post("/{promise_id}")
async def verify_promise(
    promise_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Trigger deterministic code-only re-verification for a promise."""
    data = await verify_fulfillment(db, current_user.id, promise_id)
    return ok(data.model_dump(mode="json"))
