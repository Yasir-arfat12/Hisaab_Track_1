import time
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.common import HealthChecks, HealthData, ok

router = APIRouter(tags=["Health"])

_START_TIME = time.monotonic()


def _check_llm_config() -> Literal["ok", "degraded", "error"]:
    has_any_key = any(
        [
            bool(settings.GROQ_API_KEY.get_secret_value()),
            bool(settings.GEMINI_API_KEY.get_secret_value()),
            bool(settings.MISTRAL_API_KEY.get_secret_value()),
        ]
    )
    return "ok" if has_any_key else "degraded"


@router.get("/health")
async def health(db: Annotated[AsyncSession, Depends(get_db)]) -> dict:
    """Liveness and readiness probe."""
    db_status: Literal["ok", "error"] = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db_status = "error"

    llm_status = _check_llm_config()
    overall: Literal["ok", "degraded"] = (
        "ok" if db_status == "ok" and llm_status == "ok" else "degraded"
    )
    uptime_seconds = int(time.monotonic() - _START_TIME)

    payload = HealthData(
        status=overall,
        version=settings.APP_VERSION,
        checks=HealthChecks(database=db_status, llm=llm_status),
        uptime_seconds=uptime_seconds,
    )
    return ok(payload.model_dump())
