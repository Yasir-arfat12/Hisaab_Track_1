from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.escalation import EscalationStep
from app.services import promise_service
from app.utils.exceptions import AppError, ErrorCode
from app.utils.pdf import build_dossier_pdf

DOSSIER_DIR = Path("data/dossiers")


async def build_dossier_summary(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
) -> dict[str, Any]:
    """Assemble structured dossier JSON (used by both PDF generator and MCP build_dossier)."""
    detail = await promise_service.get_promise_detail(db, user_id, promise_id)
    steps = (
        await db.execute(
            select(EscalationStep)
            .where(EscalationStep.promise_id == promise_id)
            .order_by(EscalationStep.rung.asc())
        )
    ).scalars().all()

    return {
        "promise": detail.model_dump(mode="json"),
        "timeline": [e.model_dump(mode="json") for e in detail.timeline],
        "escalation_steps": [
            {
                "rung": s.rung,
                "notice_type": s.notice_type,
                "deadline": s.deadline.isoformat(),
                "draft_generated_at": (
                    s.draft_generated_at.isoformat() if s.draft_generated_at else None
                ),
            }
            for s in steps
        ],
        "not_legal_advice_notice": settings.NOT_LEGAL_ADVICE_TEXT,
    }


def get_dossier_path(promise_id: UUID) -> Path:
    return DOSSIER_DIR / f"hisaab-dossier-{promise_id}.pdf"


async def generate_and_save_dossier_pdf(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
) -> Path:
    """Build dossier PDF with ReportLab and persist to DOSSIER_DIR."""
    summary = await build_dossier_summary(db, user_id, promise_id)
    pdf_bytes = build_dossier_pdf(summary)
    DOSSIER_DIR.mkdir(parents=True, exist_ok=True)
    path = get_dossier_path(promise_id)
    path.write_bytes(pdf_bytes)
    return path


async def load_dossier_pdf_bytes(
    db: AsyncSession,
    user_id: UUID,
    promise_id: UUID,
) -> bytes:
    """Verify ownership and return generated PDF bytes, or raise DOSSIER_GENERATION_FAILED."""
    await promise_service.get_promise_detail(db, user_id, promise_id)
    path = get_dossier_path(promise_id)
    if not path.exists():
        raise AppError(
            code=ErrorCode.DOSSIER_GENERATION_FAILED,
            message="Dossier has not been generated yet. Please enqueue generation first.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"promise_id": str(promise_id)},
        )
    return path.read_bytes()
