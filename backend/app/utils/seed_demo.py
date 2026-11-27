import asyncio

from sqlalchemy import select

from app.auth.demo import create_demo_user_with_seed
from app.database import async_session_factory, init_db
from app.models.user import User


async def seed_demo() -> None:
    """Idempotent CLI helper to ensure a demo user with seeded data exists."""
    await init_db()
    async with async_session_factory() as db:
        existing = (
            await db.execute(select(User).where(User.is_demo.is_(True), User.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if existing is None:
            await create_demo_user_with_seed(db)


if __name__ == "__main__":
    asyncio.run(seed_demo())
