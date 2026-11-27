from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.schemas.promise import PromiseCategory, PromisePatchRequest, PromiseStatus
from app.services import promise_service

router = APIRouter(prefix="/promises", tags=["Promises"])


@router.get("")
async def list_promises(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Annotated[PromiseStatus | None, Query()] = None,
    category: Annotated[PromiseCategory | None, Query()] = None,
    merchant_id: Annotated[UUID | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> dict:
    """List promises for the authenticated user with cursor pagination and filters."""
    data = await promise_service.list_promises(
        db,
        current_user.id,
        promise_status=status,
        category=category,
        merchant_id=merchant_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor=cursor,
    )
    return ok(data.model_dump(mode="json"))


@router.get("/{promise_id}")
async def get_promise(
    promise_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Retrieve full promise detail including timeline."""
    data = await promise_service.get_promise_detail(db, current_user.id, promise_id)
    return ok(data.model_dump(mode="json"))


@router.patch("/{promise_id}")
async def patch_promise(
    promise_id: UUID,
    body: PromisePatchRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update a promise's status (dismissed) or user_note."""
    data = await promise_service.patch_promise(db, current_user.id, promise_id, body)
    return ok(data.model_dump(mode="json"))
