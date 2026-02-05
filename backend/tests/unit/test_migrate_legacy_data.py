from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT))

from scripts.migrate_legacy_data import (  # noqa: E402
    LegacyDataParser,
    MigrationValidator,
    SchemaTransformer,
)


def _write_backup(tmp_path: Path, content: str) -> Path:
    backup_path = tmp_path / "backup.sql"
    backup_path.write_text(content, encoding="utf-8")
    return backup_path


def test_parser_reads_session_occurrences(tmp_path: Path) -> None:
    backup_path = _write_backup(
        tmp_path,
        """
COPY public.session_occurrences (session_id, starts_at, ends_at, cancelled, cancellation_reason, auto_generated, block_id, id) FROM stdin;
11111111-1111-1111-1111-111111111111\t2026-02-10 02:30:00+00\t2026-02-10 04:30:00+00\tf\t\\N\tt\t22222222-2222-2222-2222-222222222222\t33333333-3333-3333-3333-333333333333
\\.
""".strip(),
    )

    parser = LegacyDataParser(str(backup_path))
    assert "session_occurrences" in parser.list_tables()
    assert parser.get_row_count("session_occurrences") == 1
    row = parser.get_table("session_occurrences")["rows"][0]
    assert row["session_id"] == "11111111-1111-1111-1111-111111111111"
    assert row["block_id"] == "22222222-2222-2222-2222-222222222222"


def test_transform_occurrences_adds_audit_fields(tmp_path: Path) -> None:
    backup_path = _write_backup(
        tmp_path,
        """
COPY public.session_occurrences (session_id, starts_at, ends_at, cancelled, cancellation_reason, auto_generated, block_id, id) FROM stdin;
11111111-1111-1111-1111-111111111111\t2026-02-10 02:30:00+00\t2026-02-10 04:30:00+00\tf\t\\N\tt\t22222222-2222-2222-2222-222222222222\t33333333-3333-3333-3333-333333333333
\\.
""".strip(),
    )

    parser = LegacyDataParser(str(backup_path))
    transformer = SchemaTransformer()
    transformed = transformer.transform_all(parser)

    assert "occurrences" in transformed
    occurrence = transformed["occurrences"][0]
    assert occurrence["id"] == "33333333-3333-3333-3333-333333333333"
    assert occurrence["created_at"].startswith("2026-01-20")
    assert occurrence["updated_at"].startswith("2026-01-20")


def test_validator_detects_missing_foreign_keys() -> None:
    tables = {
        "occurrences": [
            {
                "id": "occ-1",
                "session_id": "missing-session",
                "block_id": "missing-block",
                "starts_at": "2026-02-10 02:30:00+00",
                "ends_at": "2026-02-10 04:30:00+00",
            }
        ],
        "sessions": [],
        "blocks": [],
    }

    validator = MigrationValidator(tables)
    issues = validator.validate()
    messages = [issue.message for issue in issues]

    assert any("session_id references missing sessions" in msg for msg in messages)
    assert any("block_id references missing blocks" in msg for msg in messages)


@pytest.mark.parametrize(
    "table,row",
    [
        ("sessions", {"id": "s1", "location_id": None}),
        ("students", {"id": "st1", "caregiver_id": "c1", "name": ""}),
    ],
)
def test_validator_required_fields(table: str, row: dict) -> None:
    validator = MigrationValidator({table: [row]})
    issues = validator.validate()
    assert issues
