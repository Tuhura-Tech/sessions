"""initial_schema_from_backup

Revision ID: 0001
Revises:
Create Date: 2026-02-07 00:00:00.000000

This migration replicates the exact schema from backup.sql (legacy schema).
"""

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from advanced_alchemy.types import (
    EncryptedString,
    EncryptedText,
    GUID,
    ORA_JSONB,
    DateTimeUTC,
    StoredObject,
    PasswordHash,
    FernetBackend,
)
from advanced_alchemy.types.encrypted_string import PGCryptoBackend
from advanced_alchemy.types.password_hash.passlib import PasslibHasher
from advanced_alchemy.types.password_hash.pwdlib import PwdlibHasher
from sqlalchemy import Text  # noqa: F401

if TYPE_CHECKING:
    pass

__all__ = [
    "downgrade",
    "upgrade",
    "schema_upgrades",
    "schema_downgrades",
    "data_upgrades",
    "data_downgrades",
]

sa.GUID = GUID
sa.DateTimeUTC = DateTimeUTC
sa.ORA_JSONB = ORA_JSONB
sa.EncryptedString = EncryptedString
sa.EncryptedText = EncryptedText
sa.StoredObject = StoredObject
sa.PasswordHash = PasswordHash
sa.PasslibHasher = PasslibHasher
sa.PwdlibHasher = PwdlibHasher
sa.FernetBackend = FernetBackend
sa.PGCryptoBackend = PGCryptoBackend

# revision identifiers, used by Alembic.
revision = "0003_improve_child_reporting"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            schema_upgrades()
            data_upgrades()


def downgrade() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        with op.get_context().autocommit_block():
            data_downgrades()
            schema_downgrades()


def schema_upgrades() -> None:
    """Schema upgrades - replicate backup.sql schema exactly."""

    # Create caregivers table
    op.create_table(
        "caregivers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("referral_source", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("caregivers_pkey")),
    )
    op.create_index("ix_caregivers_email", "caregivers", ["email"], unique=True)

    # Create caregiver_magic_links table
    op.create_table(
        "caregiver_magic_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("caregiver_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["caregiver_id"],
            ["caregivers.id"],
            name="caregiver_magic_links_caregiver_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("caregiver_magic_links_pkey")),
    )
    op.create_index(
        "ix_caregiver_magic_links_caregiver_id",
        "caregiver_magic_links",
        ["caregiver_id"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_magic_links_token_hash",
        "caregiver_magic_links",
        ["token_hash"],
        unique=True,
    )

    # Create caregiver_sessions table
    op.create_table(
        "caregiver_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("caregiver_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["caregiver_id"],
            ["caregivers.id"],
            name="caregiver_sessions_caregiver_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("caregiver_sessions_pkey")),
    )
    op.create_index(
        "ix_caregiver_sessions_caregiver_id",
        "caregiver_sessions",
        ["caregiver_id"],
        unique=False,
    )
    op.create_index(
        "ix_caregiver_sessions_token_hash",
        "caregiver_sessions",
        ["token_hash"],
        unique=True,
    )

    # Create children table (legacy name for students)
    op.create_table(
        "children",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("caregiver_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("media_consent", sa.Boolean(), nullable=False),
        sa.Column("medical_info", sa.String(length=1000), nullable=True),
        sa.Column("needs_devices", sa.Boolean(), nullable=False),
        sa.Column("other_info", sa.String(length=1000), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("ethnicity", sa.String(length=200), nullable=True),
        sa.Column("school_name", sa.String(length=200), nullable=True),
        sa.Column("gender", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["caregiver_id"], ["caregivers.id"], name="children_caregiver_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("children_pkey")),
    )

    # Create child_notes table
    op.create_table(
        "child_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="child_notes_child_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("child_notes_pkey")),
    )
    op.create_index(
        "ix_child_notes_child_id", "child_notes", ["child_id"], unique=False
    )

    # Create staff table
    op.create_table(
        "staff",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("sso_id", sa.String(length=255), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("staff_pkey")),
    )
    op.create_index("ix_staff_active", "staff", ["active"], unique=False)
    op.create_index("ix_staff_email", "staff", ["email"], unique=True)
    op.create_index("ix_staff_sso_id", "staff", ["sso_id"], unique=True)

    # Create exclusion_dates table
    op.create_table(
        "exclusion_dates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("exclusion_dates_pkey")),
        sa.UniqueConstraint("year", "date", name="uq_exclusion_dates_year_date"),
    )
    op.create_index(
        "ix_exclusion_dates_date", "exclusion_dates", ["date"], unique=False
    )
    op.create_index(
        "ix_exclusion_dates_year", "exclusion_dates", ["year"], unique=False
    )

    # Create session_blocks table (legacy name for blocks)
    op.create_table(
        "session_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("block_type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("session_blocks_pkey")),
        sa.UniqueConstraint("year", "block_type", name="uq_session_blocks_year_type"),
    )
    op.create_index(
        "ix_session_blocks_block_type", "session_blocks", ["block_type"], unique=False
    )
    op.create_index("ix_session_blocks_year", "session_blocks", ["year"], unique=False)

    # Create session_locations table (legacy name for locations)
    op.create_table(
        "session_locations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("instructions", sa.String(length=500), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("internal_notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("session_locations_pkey")),
    )

    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_location_id", sa.UUID(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("session_type", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("age_lower", sa.Integer(), nullable=False),
        sa.Column("age_upper", sa.Integer(), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("waitlist", sa.Boolean(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("what_to_bring", sa.Text(), nullable=True),
        sa.Column("prerequisites", sa.Text(), nullable=True),
        sa.Column("photo_album_url", sa.String(length=500), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "day_of_week IS NULL OR (day_of_week >= 0 AND day_of_week <= 6)",
            name="ck_sessions_day_of_week_nullable",
        ),
        sa.CheckConstraint(
            "(session_type = 'term' AND day_of_week IS NOT NULL) OR (session_type = 'special')",
            name="ck_sessions_term_requires_schedule",
        ),
        sa.CheckConstraint(
            "session_type IN ('term', 'special')", name="ck_sessions_type"
        ),
        sa.ForeignKeyConstraint(
            ["session_location_id"],
            ["session_locations.id"],
            name="sessions_session_location_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("sessions_pkey")),
    )
    op.create_index("ix_sessions_archived", "sessions", ["archived"], unique=False)
    op.create_index(
        "ix_sessions_session_type", "sessions", ["session_type"], unique=False
    )
    op.create_index("ix_sessions_year", "sessions", ["year"], unique=False)

    # Create session_block_links table (legacy name for block_links)
    op.create_table(
        "session_block_links",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["session_blocks.id"],
            name="session_block_links_block_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name="session_block_links_session_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("session_block_links_pkey")),
        sa.UniqueConstraint(
            "session_id", "block_id", name="uq_session_block_links_session_block"
        ),
    )
    op.create_index(
        "ix_session_block_links_block_id",
        "session_block_links",
        ["block_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_block_links_session_id",
        "session_block_links",
        ["session_id"],
        unique=False,
    )

    # Create session_occurrences table (legacy name for occurrences)
    op.create_table(
        "session_occurrences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled", sa.Boolean(), nullable=False),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("auto_generated", sa.Boolean(), nullable=False),
        sa.Column("block_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "starts_at < ends_at", name="ck_session_occurrences_time_valid"
        ),
        sa.ForeignKeyConstraint(
            ["block_id"],
            ["session_blocks.id"],
            name="session_occurrences_block_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name="session_occurrences_session_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("session_occurrences_pkey")),
    )
    op.create_index(
        "ix_session_occurrences_block_id",
        "session_occurrences",
        ["block_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_occurrences_session_id",
        "session_occurrences",
        ["session_id"],
        unique=False,
    )
    op.execute(
        "COMMENT ON COLUMN session_occurrences.auto_generated IS 'True if created by generate_occurrences, False if manually added'"
    )
    op.execute(
        "COMMENT ON COLUMN session_occurrences.block_id IS 'Which block this occurrence belongs to'"
    )

    # Create session_staff table
    op.create_table(
        "session_staff",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("staff_id", sa.UUID(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            name="session_staff_session_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff.id"],
            name="session_staff_staff_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("session_staff_pkey")),
        sa.UniqueConstraint("session_id", "staff_id", name="uq_session_staff"),
    )
    op.create_index(
        "ix_session_staff_session_id", "session_staff", ["session_id"], unique=False
    )
    op.create_index(
        "ix_session_staff_staff_id", "session_staff", ["staff_id"], unique=False
    )

    # Create signups table
    op.create_table(
        "signups",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("caregiver_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_dropoff", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'waitlisted', 'withdrawn')",
            name="ck_signups_status",
        ),
        sa.ForeignKeyConstraint(
            ["caregiver_id"], ["caregivers.id"], name="signups_caregiver_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["child_id"], ["children.id"], name="signups_child_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["sessions.id"], name="signups_session_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("signups_pkey")),
        sa.UniqueConstraint("session_id", "child_id", name="uq_signups_session_child"),
    )
    op.create_index("ix_signups_session_id", "signups", ["session_id"], unique=False)
    op.create_index("ix_signups_status", "signups", ["status"], unique=False)

    # Create attendance_records table
    op.create_table(
        "attendance_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("occurrence_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('present', 'absent_known', 'absent_unknown')",
            name="ck_attendance_records_status",
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="attendance_records_child_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"],
            ["session_occurrences.id"],
            name="attendance_records_occurrence_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attendance_records_pkey")),
    )
    op.create_index(
        "ix_attendance_records_child_id",
        "attendance_records",
        ["child_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_records_occurrence_id",
        "attendance_records",
        ["occurrence_id"],
        unique=False,
    )

    # Create attendance_audit_logs table
    op.create_table(
        "attendance_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("occurrence_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("old_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("old_reason", sa.Text(), nullable=True),
        sa.Column("new_reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
            name="attendance_audit_logs_child_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["occurrence_id"],
            ["session_occurrences.id"],
            name="attendance_audit_logs_occurrence_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("attendance_audit_logs_pkey")),
    )
    op.create_index(
        "ix_attendance_audit_logs_child_id",
        "attendance_audit_logs",
        ["child_id"],
        unique=False,
    )
    op.create_index(
        "ix_attendance_audit_logs_occurrence_id",
        "attendance_audit_logs",
        ["occurrence_id"],
        unique=False,
    )

    # Create views
    op.execute("""
        CREATE VIEW caregivers_staff AS
        SELECT id, name, email, phone, email_verified
        FROM caregivers
    """)

    op.execute("""
        CREATE VIEW children_staff AS
        SELECT id, caregiver_id, name, date_of_birth, media_consent, medical_info, needs_devices, other_info
        FROM children
    """)

    op.execute("""
        CREATE VIEW session_occurrences_public AS
        SELECT id, session_id, starts_at, ends_at, cancelled, cancellation_reason
        FROM session_occurrences
    """)

    op.execute("""
        CREATE VIEW sessions_public AS
        SELECT 
            s.id,
            s.name,
            s.age_lower,
            s.age_upper,
            s.day_of_week,
            s.start_time,
            s.end_time,
            s.year,
            s.session_type,
            s.what_to_bring,
            s.prerequisites,
            s.waitlist,
            l.id AS location_id,
            l.name AS location_name,
            l.address AS location_address,
            l.region AS location_region,
            l.lat AS location_lat,
            l.lng AS location_lng,
            l.instructions AS location_instructions
        FROM sessions s
        JOIN session_locations l ON l.id = s.session_location_id
        WHERE COALESCE(s.archived, false) = false
    """)


def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    # Drop views first
    op.execute("DROP VIEW IF EXISTS sessions_public")
    op.execute("DROP VIEW IF EXISTS session_occurrences_public")
    op.execute("DROP VIEW IF EXISTS children_staff")
    op.execute("DROP VIEW IF EXISTS caregivers_staff")

    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("attendance_audit_logs")
    op.drop_table("attendance_records")
    op.drop_table("signups")
    op.drop_table("session_staff")
    op.drop_table("session_occurrences")
    op.drop_table("session_block_links")
    op.drop_table("sessions")
    op.drop_table("session_locations")
    op.drop_table("session_blocks")
    op.drop_table("exclusion_dates")
    op.drop_table("staff")
    op.drop_table("child_notes")
    op.drop_table("children")
    op.drop_table("caregiver_sessions")
    op.drop_table("caregiver_magic_links")
    op.drop_table("caregivers")


def data_upgrades() -> None:
    """Add optional data upgrade migrations here!"""
    pass


def data_downgrades() -> None:
    """Add optional data downgrade migrations here!"""
    pass
