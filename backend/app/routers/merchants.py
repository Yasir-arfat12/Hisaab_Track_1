from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.services import merchant_service

router = APIRouter(prefix="/merchants", tags=["Merchant"])


@router.get("/{merchant_id}/record")
async def get_merchant_record(
    merchant_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return promise-keeping stats for a merchant based on user data."""
    data = await merchant_service.get_merchant_record(db, current_user.id, merchant_id)
    return ok(data.model_dump(mode="json"))
