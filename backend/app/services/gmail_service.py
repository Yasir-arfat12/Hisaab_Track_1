import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.email import Email
from app.models.finance import BankCredit
from app.models.job import Job
from app.models.promise import Merchant, Promise
from app.models.user import GmailSyncState, OAuthToken
from app.services.extraction_service import extract_promises
from app.services.verification_service import verify_fulfillment
from app.utils.email_parser import compute_body_hash, parse_bank_alert_email
from app.utils.encryption import decrypt_token, encrypt_token
from app.utils.exceptions import AppError, ErrorCode
from app.utils.fuzzy import normalize_merchant_name

logger = structlog.get_logger(__name__)

GMAIL_MESSAGES_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_QUERY = (
    "newer_than:90d "
    "(refund OR claim OR settlement OR credited OR reversal OR cancellation OR order)"
)


async def refresh_gmail_access_token(
    db: AsyncSession,
    oauth_token: OAuthToken,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> str:
    """Return a valid Gmail access token, refreshing if expired."""
    now = datetime.now(UTC)
    expires_at = oauth_token.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at is None or expires_at > now + timedelta(seconds=60):
        return decrypt_token(oauth_token.access_token_enc)

    if not oauth_token.refresh_token_enc:
        raise AppError(
            code=ErrorCode.GMAIL_AUTH_EXPIRED,
            message="Gmail OAuth token expired and no refresh token is available",
            status_code=401,
        )

    refresh_tok = decrypt_token(oauth_token.refresh_token_enc)
    data = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
        "refresh_token": refresh_tok,
        "grant_type": "refresh_token",
    }
    if http_client is not None:
        resp = await http_client.post(GOOGLE_TOKEN_URL, data=data, timeout=15.0)
    else:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data)

    if resp.status_code != 200:
        raise AppError(
            code=ErrorCode.GMAIL_AUTH_EXPIRED,
            message="Gmail OAuth token expired or revoked",
            status_code=401,
        )

    tok_json = resp.json()
    new_access = tok_json["access_token"]
    oauth_token.access_token_enc = encrypt_token(new_access)
    if "expires_in" in tok_json:
        oauth_token.expires_at = now + timedelta(seconds=int(tok_json["expires_in"]))
    await db.commit()
    return str(new_access)


def _decode_b64_body(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")


def _extract_payload_text(payload: dict[str, Any]) -> str:
    body = payload.get("body") or {}
    if body.get("data"):
        return _decode_b64_body(str(body["data"]))
    for part in payload.get("parts") or []:
        mime = str(part.get("mimeType", ""))
        if mime == "text/plain" and (part.get("body") or {}).get("data"):
            return _decode_b64_body(str(part["body"]["data"]))
    for part in payload.get("parts") or []:
        nested = _extract_payload_text(part)
        if nested:
            return nested
    return ""


def _header_value(headers: list[dict[str, Any]], name: str) -> str:
    target = name.lower()
    for h in headers:
        if str(h.get("name", "")).lower() == target:
            return str(h.get("value", ""))
    return ""


async def _get_or_create_merchant(db: AsyncSession, name: str) -> Merchant:
    norm = normalize_merchant_name(name) or "unknown merchant"
    existing = (
        await db.execute(select(Merchant).where(Merchant.normalized_name == norm))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    merchant = Merchant(id=uuid4(), name=name[:255], normalized_name=norm)
    db.add(merchant)
    await db.flush()
    return merchant


async def sync_gmail_for_user(
    db: AsyncSession,
    user_id: UUID,
    job: Job,
    *,
    full_resync: bool = False,
    http_client: httpx.AsyncClient | None = None,
    max_pages: int = 50,
) -> dict[str, int]:
    """
    Paginated, idempotent, resumable Gmail sync for a user.
    Saves next_page_token after every page and purges raw email bodies after extraction.
    """
    job.status = "running"
    job.progress = 5
    await db.commit()

    oauth_token = (
        await db.execute(
            select(OAuthToken).where(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == "google",
            )
        )
    ).scalar_one_or_none()
    if oauth_token is None:
        job.status = "failed"
        job.error_msg = "GMAIL_AUTH_EXPIRED"
        await db.commit()
        raise AppError(
            code=ErrorCode.GMAIL_AUTH_EXPIRED,
            message="Gmail is not connected or token expired",
            status_code=401,
        )

    sync_state = (
        await db.execute(select(GmailSyncState).where(GmailSyncState.user_id == user_id))
    ).scalar_one_or_none()
    if sync_state is None:
        sync_state = GmailSyncState(id=uuid4(), user_id=user_id, status="running")
        db.add(sync_state)
        await db.flush()
    else:
        sync_state.status = "running"
        if full_resync:
            sync_state.next_page_token = None
    await db.commit()

    emails_scanned = 0
    promises_extracted = 0
    credits_extracted = 0

    try:
        access_token = await refresh_gmail_access_token(
            db, oauth_token, http_client=http_client
        )
        headers = {"Authorization": f"Bearer {access_token}"}
        page_token = sync_state.next_page_token
        pages_processed = 0

        async def _get(url: str, params: dict[str, Any] | None = None) -> httpx.Response:
            if http_client is not None:
                return await http_client.get(url, headers=headers, params=params, timeout=20.0)
            async with httpx.AsyncClient(timeout=20.0) as client:
                return await client.get(url, headers=headers, params=params)

        while pages_processed < max_pages:
            params: dict[str, Any] = {"q": GMAIL_QUERY, "maxResults": 50}
            if page_token:
                params["pageToken"] = page_token

            list_resp = await _get(GMAIL_MESSAGES_URL, params=params)
            if list_resp.status_code == 401:
                raise AppError(
                    code=ErrorCode.GMAIL_AUTH_EXPIRED,
                    message="Gmail access expired",
                    status_code=401,
                )
            list_resp.raise_for_status()
            list_json = list_resp.json()
            messages = list_json.get("messages") or []

            for msg_ref in messages:
                msg_id = str(msg_ref["id"])
                existing_email = (
                    await db.execute(
                        select(Email.id).where(Email.gmail_message_id == msg_id)
                    )
                ).scalar_one_or_none()
                if existing_email is not None:
                    continue

                msg_resp = await _get(f"{GMAIL_MESSAGES_URL}/{msg_id}", params={"format": "full"})
                msg_resp.raise_for_status()
                msg_data = msg_resp.json()
                payload = msg_data.get("payload") or {}
                msg_headers = payload.get("headers") or []
                sender = _header_value(msg_headers, "From") or "unknown@example.com"
                subject = _header_value(msg_headers, "Subject")
                internal_ms = int(msg_data.get("internalDate") or 0)
                received_at = (
                    datetime.fromtimestamp(internal_ms / 1000.0, tz=UTC)
                    if internal_ms > 0
                    else datetime.now(UTC)
                )
                body_text = _extract_payload_text(payload) or str(msg_data.get("snippet", ""))
                body_hash = compute_body_hash(body_text)

                dup_hash = (
                    await db.execute(
                        select(Email.id).where(
                            Email.user_id == user_id,
                            Email.body_hash == body_hash,
                        )
                    )
                ).scalar_one_or_none()
                if dup_hash is not None:
                    continue

                email_row = Email(
                    id=uuid4(),
                    user_id=user_id,
                    gmail_message_id=msg_id,
                    thread_id=msg_data.get("threadId"),
                    sender=sender[:500],
                    subject=subject,
                    received_at=received_at,
                    body_hash=body_hash,
                    body_text=body_text,
                )
                db.add(email_row)
                await db.flush()
                emails_scanned += 1

                # 1. Check if this is a bank credit alert email
                bank_alert = parse_bank_alert_email(
                    sender=sender,
                    subject=subject,
                    body_text=body_text,
                    received_at=received_at,
                )
                if bank_alert is not None:
                    c_hash = hashlib.sha256(
                        f"{user_id}:{bank_alert.amount_paise}:{bank_alert.credited_at.date().isoformat()}:{bank_alert.narration}".encode()
                    ).hexdigest()
                    dup_credit = (
                        await db.execute(
                            select(BankCredit.id).where(BankCredit.credit_hash == c_hash)
                        )
                    ).scalar_one_or_none()
                    if dup_credit is None:
                        db.add(
                            BankCredit(
                                id=uuid4(),
                                user_id=user_id,
                                source="email",
                                amount_paise=bank_alert.amount_paise,
                                credited_at=bank_alert.credited_at,
                                narration=bank_alert.narration,
                                credit_hash=c_hash,
                            )
                        )
                        credits_extracted += 1

                # 2. Extract promises (LLM + deterministic fallback)
                candidates = await extract_promises(
                    body_text,
                    sender=sender,
                    received_at=received_at,
                    db=db,
                    http_client=http_client,
                )
                for cand in candidates:
                    merchant = await _get_or_create_merchant(db, cand.merchant)
                    db.add(
                        Promise(
                            id=uuid4(),
                            user_id=user_id,
                            email_id=email_row.id,
                            merchant_id=merchant.id,
                            merchant_name=merchant.name,
                            category=cand.category,
                            amount_paise=cand.amount_paise,
                            due_date=cand.due_date,
                            exact_quote=cand.exact_quote,
                            confidence=cand.confidence,
                            status=cand.status,
                            extraction_method=cand.extraction_method,
                            needs_review_reason=cand.needs_review_reason,
                        )
                    )
                    promises_extracted += 1

                # 3. Purge raw email body immediately after extraction
                now = datetime.now(UTC)
                email_row.processed_at = now
                email_row.body_text = None
                email_row.purged_at = now

            pages_processed += 1
            page_token = list_json.get("nextPageToken")
            sync_state.next_page_token = page_token
            job.progress = min(90, 10 + pages_processed * 15)
            await db.commit()

            if not page_token:
                break

        # Verify open promises against newly ingested credits
        open_promises = (
            await db.execute(
                select(Promise.id).where(
                    Promise.user_id == user_id,
                    Promise.status.in_(["pending", "overdue"]),
                )
            )
        ).scalars().all()
        for pid in open_promises:
            await verify_fulfillment(db, user_id, pid)

        sync_state.status = "idle"
        sync_state.last_synced_at = datetime.now(UTC)
        sync_state.next_page_token = None
        result = {
            "emails_scanned": emails_scanned,
            "promises_extracted": promises_extracted,
            "credits_extracted": credits_extracted,
        }
        job.status = "done"
        job.progress = 100
        job.result_json = result
        await db.commit()
        return result

    except Exception as exc:
        sync_state.status = "failed"
        job.status = "failed"
        job.error_msg = str(exc)
        await db.commit()
        raise
