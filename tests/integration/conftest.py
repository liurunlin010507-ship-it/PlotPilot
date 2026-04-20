"""集成测试共享 fixture：内存 SQLite + 全量迁移。"""

from pathlib import Path

import pytest
from infrastructure.persistence.database.connection import (
    DatabaseConnection,
    _apply_autopilot_v2_migrations,
    _apply_character_enhancements,
    _apply_chapter_summaries_enhancements,
    _apply_last_chapter_audit_columns,
    _apply_migration_files,
    _ensure_triple_provenance_table,
    _migrate_triples_columns,
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "infrastructure" / "persistence" / "database" / "schema.sql"


def _apply_all_migrations(conn):
    _migrate_triples_columns(conn)
    _apply_autopilot_v2_migrations(conn)
    _apply_last_chapter_audit_columns(conn)
    _apply_character_enhancements(conn)
    _apply_chapter_summaries_enhancements(conn)
    _ensure_triple_provenance_table(conn)
    _apply_migration_files(conn)
    conn.commit()


@pytest.fixture
def db():
    """内存 SQLite 数据库（含 schema + 全量迁移），测试结束自动关闭。"""
    db = DatabaseConnection(":memory:")
    conn = db.get_connection()
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    _apply_all_migrations(conn)
    yield db
    db.close()
