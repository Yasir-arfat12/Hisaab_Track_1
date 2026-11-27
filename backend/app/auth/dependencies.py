from typing import Annotated

from fastapi import Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session import decode_session_token
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.utils.exceptions import AppError, ErrorCode


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve authenticated User from the httpOnly session cookie."""
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise AppError(
            code=ErrorCode.AUTH_REQUIRED,
            message="Authentication required",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    user_id = decode_session_token(token)
    result = await db.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise AppError(
            code=ErrorCode.AUTH_REQUIRED,
            message="Session expired or not found",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return user
