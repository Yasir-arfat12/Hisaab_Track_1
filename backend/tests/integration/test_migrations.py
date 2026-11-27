import asyncio
import sqlite3
import tempfile
from pathlib import Path

from alembic.config import Config

from alembic import command

EXPECTED_TABLES = {
    "users",
    "oauth_tokens",
    "gmail_sync_state",
    "emails",
    "merchants",
    "promises",
    "bank_credits",
    "verification_matches",
    "escalation_steps",
    "jobs",
    "llm_cache",
    "idempotency_keys",
}


def _get_sqlite_tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version'"
        ).fetchall()
    finally:
        conn.close()
    return {row[0] for row in rows}


def _run_upgrade_and_downgrade(db_path: Path) -> tuple[set[str], set[str], set[str]]:
    backend_dir = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path.as_posix()}")

    command.upgrade(cfg, "head")
    tables_after_up = _get_sqlite_tables(db_path)

    command.downgrade(cfg, "base")
    tables_after_down = _get_sqlite_tables(db_path)

    command.upgrade(cfg, "head")
    tables_after_reup = _get_sqlite_tables(db_path)

    return tables_after_up, tables_after_down, tables_after_reup


async def test_alembic_migration_up_and_down() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "migration_test.db"
        # Run Alembic in a worker thread because env.py uses asyncio.run().
        up_tables, down_tables, reup_tables = await asyncio.to_thread(
            _run_upgrade_and_downgrade, db_path
        )

    assert up_tables == EXPECTED_TABLES
    assert down_tables == set()
    assert reup_tables == EXPECTED_TABLES
