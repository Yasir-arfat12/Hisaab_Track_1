from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import BankCredit, VerificationMatch
from app.models.promise import Merchant, Promise
from app.schemas.merchant import MerchantRecordData
from app.utils.exceptions import AppError, ErrorCode


async def get_merchant_record(
    db: AsyncSession,
    user_id: UUID,
    merchant_id: UUID,
) -> MerchantRecordData:
    """Compute promise-keeping record for a merchant from the user's own promises."""
    merchant = (
        await db.execute(select(Merchant).where(Merchant.id == merchant_id))
    ).scalar_one_or_none()
    if merchant is None:
        raise AppError(
            code=ErrorCode.NOT_FOUND,
            message="Merchant not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"merchant_id": str(merchant_id)},
        )

    promises = (
        await db.execute(
            select(Promise).where(
                Promise.user_id == user_id,
                Promise.merchant_id == merchant_id,
            )
        )
    ).scalars().all()

    total_promises = len(promises)
    kept_count = sum(1 for p in promises if p.status == "kept")
    overdue_count = sum(1 for p in promises if p.status == "overdue")
    dismissed_count = sum(1 for p in promises if p.status == "dismissed")

    non_dismissed = total_promises - dismissed_count
    keep_rate_pct = round((kept_count / non_dismissed) * 100.0, 1) if non_dismissed > 0 else 0.0

    # Average resolution days for kept promises that have a matched bank credit
    kept_ids = [p.id for p in promises if p.status == "kept"]
    avg_days: float | None = None
    if kept_ids:
        matches = (
            await db.execute(
                select(Promise, BankCredit)
                .join(VerificationMatch, VerificationMatch.promise_id == Promise.id)
                .join(BankCredit, BankCredit.id == VerificationMatch.credit_id)
                .where(Promise.id.in_(kept_ids))
            )
        ).all()
        diffs: list[int] = []
        for p, c in matches:
            delta = (c.credited_at.date() - p.created_at.date()).days
            diffs.append(max(0, delta))
        if diffs:
            avg_days = round(sum(diffs) / len(diffs), 1)

    return MerchantRecordData(
        merchant_id=merchant.id,
        merchant_name=merchant.name,
        total_promises=total_promises,
        kept_count=kept_count,
        overdue_count=overdue_count,
        dismissed_count=dismissed_count,
        average_resolution_days=avg_days,
        keep_rate_pct=keep_rate_pct,
    )
