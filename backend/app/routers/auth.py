from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.demo import DEMO_SEED_SCENARIO, create_demo_user_with_seed
from app.auth.dependencies import get_current_user
from app.auth.oauth import (
    GMAIL_READONLY_SCOPE,
    build_google_auth_url,
    create_oauth_state,
    exchange_code_for_tokens,
    fetch_google_userinfo,
    revoke_google_token,
    verify_oauth_state,
)
from app.auth.session import clear_session_cookies, set_session_cookies
from app.config import settings
from app.database import get_db
from app.models.email import Email
from app.models.finance import BankCredit
from app.models.job import Job
from app.models.promise import Promise
from app.models.user import GmailSyncState, OAuthToken, User
from app.schemas.auth import (
    DeleteAccountData,
    DemoAuthData,
    GoogleCallbackData,
    GoogleStartData,
    LogoutData,
    UserProfileData,
)
from app.schemas.common import ok
from app.services.purge_service import delete_user_dossiers
from app.utils.encryption import decrypt_token, encrypt_token
from app.utils.exceptions import AppError, ErrorCode

router = APIRouter(prefix="/auth", tags=["Auth"])

OAUTH_STATE_COOKIE = "oauth_state"


def _to_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


@router.get("/google/start")
async def google_start(response: Response) -> dict:
    """Return Google OAuth authorization URL and set anti-CSRF state cookie."""
    state = create_oauth_state()
    redirect_url = build_google_auth_url(state)
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        max_age=600,
        path="/",
    )
    return ok(GoogleStartData(redirect_url=redirect_url).model_dump(mode="json"))


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: Annotated[str, Query(min_length=1)],
    state: Annotated[str, Query(min_length=1)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Exchange Google OAuth code for tokens, encrypt tokens, and set session cookie."""
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    verify_oauth_state(state, cookie_state)
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")

    token_data = await exchange_code_for_tokens(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Google OAuth did not return an access token",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    userinfo = await fetch_google_userinfo(access_token)
    email = userinfo.get("email")
    if not email:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Google user profile missing email",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    display_name = userinfo.get("name") or email.split("@")[0]
    picture_url = userinfo.get("picture")

    user_res = await db.execute(select(User).where(User.email == email))
    user = user_res.scalar_one_or_none()
    if user is None:
        user = User(
            id=uuid4(),
            email=email,
            name=display_name,
            picture_url=picture_url,
            is_demo=False,
        )
        db.add(user)
        await db.flush()
    else:
        user.name = display_name
        user.picture_url = picture_url
        user.deleted_at = None

    expires_in = token_data.get("expires_in")
    expires_at = (
        datetime.now(UTC) + timedelta(seconds=int(expires_in)) if expires_in is not None else None
    )
    refresh_token = token_data.get("refresh_token")
    scope = token_data.get("scope") or GMAIL_READONLY_SCOPE

    tok_res = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == "google",
        )
    )
    oauth_token = tok_res.scalar_one_or_none()
    if oauth_token is None:
        oauth_token = OAuthToken(
            id=uuid4(),
            user_id=user.id,
            provider="google",
            access_token_enc=encrypt_token(access_token),
            refresh_token_enc=encrypt_token(refresh_token) if refresh_token else None,
            expires_at=expires_at,
            scope=scope,
        )
        db.add(oauth_token)
    else:
        oauth_token.access_token_enc = encrypt_token(access_token)
        if refresh_token:
            oauth_token.refresh_token_enc = encrypt_token(refresh_token)
        oauth_token.expires_at = expires_at
        oauth_token.scope = scope

    await db.commit()
    await db.refresh(user)

    set_session_cookies(response, user.id)
    payload = GoogleCallbackData(
        user_id=user.id,
        email=user.email,
        display_name=user.name,
        created_at=_to_utc(user.created_at),
    )
    return ok(payload.model_dump(mode="json"))


@router.post("/demo")
async def demo_login(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Create a seeded demo user and set httpOnly session cookie."""
    user = await create_demo_user_with_seed(db)
    set_session_cookies(response, user.id)
    payload = DemoAuthData(
        user_id=user.id,
        email=user.email,
        display_name=user.name,
        is_demo=True,
        seed_scenario=DEMO_SEED_SCENARIO,
    )
    return ok(payload.model_dump(mode="json"))


@router.post("/logout")
async def logout(
    response: Response,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Clear session and CSRF cookies."""
    clear_session_cookies(response)
    return ok(LogoutData(logged_out=True).model_dump(mode="json"))


@router.get("/me")
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return the currently authenticated user's profile."""
    tok_res = await db.execute(
        select(OAuthToken.id).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == "google",
        )
    )
    gmail_connected = tok_res.scalar_one_or_none() is not None
    payload = UserProfileData(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.name,
        is_demo=current_user.is_demo,
        gmail_connected=gmail_connected,
        created_at=_to_utc(current_user.created_at),
    )
    return ok(payload.model_dump(mode="json"))


@router.delete("/me")
async def delete_me(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Revoke OAuth tokens, purge user data, soft-delete user, and clear cookies."""
    tok_res = await db.execute(
        select(OAuthToken).where(
            OAuthToken.user_id == current_user.id,
            OAuthToken.provider == "google",
        )
    )
    tokens = tok_res.scalars().all()
    for tok in tokens:
        raw_token = decrypt_token(tok.refresh_token_enc or tok.access_token_enc)
        await revoke_google_token(raw_token)

    await delete_user_dossiers(db, current_user.id)
    await db.execute(delete(OAuthToken).where(OAuthToken.user_id == current_user.id))
    await db.execute(delete(GmailSyncState).where(GmailSyncState.user_id == current_user.id))
    await db.execute(delete(Promise).where(Promise.user_id == current_user.id))
    await db.execute(delete(Email).where(Email.user_id == current_user.id))
    await db.execute(delete(BankCredit).where(BankCredit.user_id == current_user.id))
    await db.execute(delete(Job).where(Job.user_id == current_user.id))

    current_user.deleted_at = datetime.now(UTC)
    await db.commit()

    clear_session_cookies(response)
    return ok(DeleteAccountData(deleted=True).model_dump(mode="json"))
