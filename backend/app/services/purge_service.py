from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cache import IdempotencyKey, LlmCache
from app.models.promise import Promise
from app.models.user import User
from app.services.dossier_service import get_dossier_path


async def delete_user_dossiers(db: AsyncSession, user_id: UUID) -> int:
    """Delete any generated dossier PDF files on disk for a user's promises."""
    promise_ids = (
        await db.execute(select(Promise.id).where(Promise.user_id == user_id))
    ).scalars().all()
    removed = 0
    for pid in promise_ids:
        path = get_dossier_path(pid)
        if path.exists():
            path.unlink()
            removed += 1
    return removed


async def purge_expired_demo_users(db: AsyncSession, max_age_hours: int = 24) -> int:
    """Purge synthetic demo users older than max_age_hours."""
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    expired_ids = (
        await db.execute(
            select(User.id).where(User.is_demo.is_(True), User.created_at < cutoff)
        )
    ).scalars().all()
    if not expired_ids:
        return 0
    for uid in expired_ids:
        await delete_user_dossiers(db, uid)
    await db.execute(delete(User).where(User.id.in_(expired_ids)))
    await db.commit()
    return len(expired_ids)


async def purge_expired_cache_and_idempotency(db: AsyncSession) -> tuple[int, int]:
    """Delete expired llm_cache and idempotency_keys rows."""
    now = datetime.now(UTC)
    llm_res = await db.execute(delete(LlmCache).where(LlmCache.expires_at <= now))
    idem_res = await db.execute(delete(IdempotencyKey).where(IdempotencyKey.expires_at <= now))
    await db.commit()
    llm_count = int(cast(CursorResult[Any], llm_res).rowcount or 0)
    idem_count = int(cast(CursorResult[Any], idem_res).rowcount or 0)
    return llm_count, idem_count
