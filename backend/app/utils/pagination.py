import base64
import json
from datetime import datetime
from uuid import UUID

from fastapi import status

from app.utils.exceptions import AppError, ErrorCode


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    """Encode (created_at, id) into an opaque URL-safe base64 cursor."""
    payload = {"created_at": created_at.isoformat(), "id": str(item_id)}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode an opaque cursor back into (created_at, UUID)."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
        created_at = datetime.fromisoformat(payload["created_at"])
        item_id = UUID(payload["id"])
        return created_at, item_id
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise AppError(
            code=ErrorCode.VALIDATION_ERROR,
            message="Invalid pagination cursor",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field": "cursor"},
        ) from exc
