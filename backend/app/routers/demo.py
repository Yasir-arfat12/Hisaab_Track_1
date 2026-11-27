from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import ok
from app.schemas.demo import DemoSimulateRequest
from app.services import demo_service

router = APIRouter(prefix="/demo", tags=["Demo"])


@router.post("/simulate")
async def simulate_demo(
    body: DemoSimulateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Apply a demo scenario mutation on a demo account."""
    data = await demo_service.simulate_demo_scenario(db, current_user, body)
    return ok(data.model_dump(mode="json"))
