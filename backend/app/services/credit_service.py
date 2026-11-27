import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import BankCredit, VerificationMatch
from app.schemas.finance import BankCreditItem, BankCreditListData
from app.utils.exceptions import AppError, ErrorCode
from app.utils.pagination import decode_cursor, encode_cursor

REQUIRED_CSV_COLUMNS = ("date", "description", "amount", "reference_number")


@dataclass(frozen=True)
class ParsedCsvCreditRow:
    credit_date: date
    description: str
    amount_paise: int
    reference_number: str | None
    raw_line: str


def _decode_csv_bytes(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AppError(
        code=ErrorCode.CREDIT_UPLOAD_FAILED,
        message="Unable to decode CSV file encoding",
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


def _parse_date(value: str) -> date:
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {cleaned}")


def parse_and_validate_csv(raw_bytes: bytes) -> list[ParsedCsvCreditRow]:
    """Validate required CSV columns and parse each row into integer paise."""
    text = _decode_csv_bytes(raw_bytes)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AppError(
            code=ErrorCode.CREDIT_UPLOAD_FAILED,
            message="CSV file is empty or missing header row",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"missing_columns": list(REQUIRED_CSV_COLUMNS)},
        )

    normalized_map = {col.strip().lower(): col for col in reader.fieldnames if col}
    missing = [col for col in REQUIRED_CSV_COLUMNS if col not in normalized_map]
    if missing:
        raise AppError(
            code=ErrorCode.CREDIT_UPLOAD_FAILED,
            message=f"CSV is missing required column(s): {', '.join(missing)}",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            details={"missing_columns": missing},
        )

    rows: list[ParsedCsvCreditRow] = []
    for idx, row in enumerate(reader, start=2):
        raw_date = (row.get(normalized_map["date"]) or "").strip()
        raw_desc = (row.get(normalized_map["description"]) or "").strip()
        raw_amt = (row.get(normalized_map["amount"]) or "").strip()
        raw_ref = (row.get(normalized_map["reference_number"]) or "").strip() or None

        if not raw_date and not raw_desc and not raw_amt:
            continue

        try:
            parsed_date = _parse_date(raw_date)
            amt_float = float(raw_amt.replace(",", ""))
            if amt_float <= 0:
                continue
            amount_paise = round(amt_float * 100)
        except ValueError as exc:
            raise AppError(
                code=ErrorCode.CREDIT_UPLOAD_FAILED,
                message=f"Invalid CSV row at line {idx}",
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                details={"line": idx},
            ) from exc

        rows.append(
            ParsedCsvCreditRow(
                credit_date=parsed_date,
                description=raw_desc or "Bank credit",
                amount_paise=amount_paise,
                reference_number=raw_ref,
                raw_line=f"{raw_date},{raw_desc},{raw_amt},{raw_ref or ''}",
            )
        )

    return rows


async def insert_csv_credits(
    db: AsyncSession,
    user_id: UUID,
    rows: list[ParsedCsvCreditRow],
    *,
    bank_name: str,
    account_last4: str | None = None,
) -> int:
    """Insert parsed CSV rows idempotently using credit_hash."""
    inserted = 0
    prefix = f"[{bank_name}{f' ****{account_last4}' if account_last4 else ''}] "
    for row in rows:
        narration = f"{prefix}{row.description}"
        if row.reference_number:
            narration = f"{narration} REF {row.reference_number}"
        credit_hash = hashlib.sha256(
            f"{user_id}:{row.amount_paise}:{row.credit_date.isoformat()}:{narration}".encode()
        ).hexdigest()
        existing = (
            await db.execute(select(BankCredit.id).where(BankCredit.credit_hash == credit_hash))
        ).scalar_one_or_none()
        if existing is not None:
            continue

        db.add(
            BankCredit(
                id=uuid4(),
                user_id=user_id,
                source="csv",
                amount_paise=row.amount_paise,
                credited_at=datetime.combine(row.credit_date, datetime.min.time(), tzinfo=UTC),
                narration=narration,
                raw_line=row.raw_line,
                credit_hash=credit_hash,
            )
        )
        inserted += 1

    await db.commit()
    return inserted


async def list_credits(
    db: AsyncSession,
    user_id: UUID,
    *,
    matched: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 20,
    cursor: str | None = None,
) -> BankCreditListData:
    stmt = (
        select(BankCredit, VerificationMatch.promise_id)
        .outerjoin(VerificationMatch, VerificationMatch.credit_id == BankCredit.id)
        .where(BankCredit.user_id == user_id)
    )

    if matched is True:
        stmt = stmt.where(VerificationMatch.promise_id.is_not(None))
    elif matched is False:
        stmt = stmt.where(VerificationMatch.promise_id.is_(None))

    if date_from is not None:
        stmt = stmt.where(
            BankCredit.credited_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        )
    if date_to is not None:
        stmt = stmt.where(
            BankCredit.credited_at <= datetime.combine(date_to, datetime.max.time(), tzinfo=UTC)
        )

    if cursor is not None:
        c_created_at, c_id = decode_cursor(cursor)
        stmt = stmt.where(
            or_(
                BankCredit.created_at < c_created_at,
                and_(BankCredit.created_at == c_created_at, BankCredit.id < c_id),
            )
        )

    stmt = stmt.order_by(BankCredit.created_at.desc(), BankCredit.id.desc()).limit(limit + 1)
    rows = list((await db.execute(stmt)).all())
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = (
        encode_cursor(page_rows[-1][0].created_at, page_rows[-1][0].id)
        if has_more and page_rows
        else None
    )

    items: list[BankCreditItem] = []
    for credit, matched_promise_id in page_rows:
        bank_name = "Bank"
        if credit.narration.startswith("[") and "]" in credit.narration:
            bank_name = credit.narration[1 : credit.narration.index("]")].split()[0]
        items.append(
            BankCreditItem(
                credit_id=credit.id,
                date=credit.credited_at.date(),
                description=credit.narration,
                amount_paise=credit.amount_paise,
                reference_number=None,
                matched_promise_id=matched_promise_id,
                bank_name=bank_name,
            )
        )

    return BankCreditListData(
        items=items,
        next_cursor=next_cursor,
        prev_cursor=None,
        limit=limit,
    )
