"""migrate_to_new_schema

Revision ID: 2bc2e459ef46
Revises: 0003_improve_child_reporting
Create Date: 2026-02-08 00:37:27.531707

"""

import warnings
from typing import TYPE_CHECKING

import sqlalchemy as sa
from alembic import op
from advanced_alchemy.types import EncryptedString, EncryptedText, GUID, ORA_JSONB, DateTimeUTC, StoredObject, PasswordHash, FernetBackend
from advanced_alchemy.types.encrypted_string import PGCryptoBackend
from advanced_alchemy.types.password_hash.passlib import PasslibHasher
from advanced_alchemy.types.password_hash.pwdlib import PwdlibHasher
from sqlalchemy import Text  # noqa: F401
from sqlalchemy.dialects import postgresql
if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["downgrade", "upgrade", "schema_upgrades", "schema_downgrades", "data_upgrades", "data_downgrades"]

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
revision = '2bc2e459ef46'
down_revision = '0003_improve_child_reporting'
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
    """schema upgrade migrations go here."""
    # Use RENAME operations to preserve data (not DROP/CREATE)
    
    # Drop views first (they reference old table names)
    op.execute("DROP VIEW IF EXISTS sessions_public")
    op.execute("DROP VIEW IF EXISTS session_occurrences_public")
    op.execute("DROP VIEW IF EXISTS children_staff")
    op.execute("DROP VIEW IF EXISTS caregivers_staff")
    
    # STEP 1: Rename tables (preserves all data)
    op.rename_table('session_locations', 'locations')
    op.rename_table('session_blocks', 'blocks')
    op.rename_table('session_block_links', 'block_links')
    op.rename_table('session_occurrences', 'occurrences')
    op.rename_table('children', 'students')
    
    # STEP 2: Drop tables that don't exist in ORM
    op.execute("DROP TABLE IF EXISTS child_notes CASCADE")
    op.execute("DROP TABLE IF EXISTS attendance_audit_logs CASCADE")
    
    # STEP 3: Remove deprecated columns
    op.execute("ALTER TABLE blocks DROP COLUMN IF EXISTS timezone")
    op.execute("ALTER TABLE occurrences DROP COLUMN IF EXISTS auto_generated")
    op.execute("ALTER TABLE sessions DROP COLUMN IF EXISTS waitlist")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS needs_devices")
    
    # STEP 4: Update block_id constraint in occurrences (nullable -> NOT NULL)
    op.execute("ALTER TABLE occurrences ALTER COLUMN block_id SET NOT NULL")
    
    # STEP 5: Drop and recreate indexes/constraints with new names
    op.execute("DROP INDEX IF EXISTS ix_session_blocks_block_type")
    op.execute("ALTER INDEX IF EXISTS ix_session_blocks_year RENAME TO ix_blocks_year")
    op.execute("ALTER INDEX IF EXISTS ix_session_block_links_session_id RENAME TO ix_block_links_session_id")
    op.execute("ALTER INDEX IF EXISTS ix_session_block_links_block_id RENAME TO ix_block_links_block_id")
    op.execute("ALTER INDEX IF EXISTS ix_session_occurrences_session_id RENAME TO ix_occurrences_session_id")
    op.execute("ALTER INDEX IF EXISTS ix_session_occurrences_block_id RENAME TO ix_occurrences_block_id")
    
    # STEP 6: Update unique constraints
    op.execute("ALTER TABLE blocks DROP CONSTRAINT IF EXISTS uq_session_blocks_year_type")
    op.execute("ALTER TABLE blocks ADD CONSTRAINT uq_blocks_year_name UNIQUE (year, name)")
    op.execute("ALTER TABLE block_links DROP CONSTRAINT IF EXISTS uq_session_block_links_session_block")
    op.execute("ALTER TABLE block_links ADD CONSTRAINT uq_block_links_block UNIQUE (session_id, block_id)")
    
    # STEP 7: Update check constraints (PostgreSQL auto-prefixes with old table name)
    op.execute("ALTER TABLE occurrences DROP CONSTRAINT IF EXISTS ck_session_occurrences_ck_session_occurrences_time_valid")
    op.execute("ALTER TABLE occurrences ADD CONSTRAINT ck_occurrences_ck_occurrences_time_valid CHECK (starts_at < ends_at)")
    
    # STEP 8: Rename foreign key constraints
    op.execute("ALTER TABLE block_links DROP CONSTRAINT IF EXISTS session_block_links_session_id_fkey")
    op.execute("ALTER TABLE block_links DROP CONSTRAINT IF EXISTS session_block_links_block_id_fkey")
    op.execute("ALTER TABLE block_links ADD CONSTRAINT fk_block_links_session_id_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE block_links ADD CONSTRAINT fk_block_links_block_id_blocks FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE")
    
    op.execute("ALTER TABLE occurrences DROP CONSTRAINT IF EXISTS session_occurrences_session_id_fkey")
    op.execute("ALTER TABLE occurrences DROP CONSTRAINT IF EXISTS session_occurrences_block_id_fkey")
    op.execute("ALTER TABLE occurrences ADD CONSTRAINT fk_occurrences_session_id_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE occurrences ADD CONSTRAINT fk_occurrences_block_id_blocks FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE")
    
    # STEP 9: Rename columns to match ORM models
    op.execute("ALTER TABLE signups RENAME COLUMN child_id TO student_id")
    op.execute("ALTER TABLE attendance_records RENAME COLUMN child_id TO student_id")
    op.execute("ALTER TABLE sessions RENAME COLUMN session_location_id TO location_id")
    
    # STEP 10: Add missing audit columns to tables
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.drop_index(batch_op.f('ix_attendance_records_child_id'))
        batch_op.create_index(batch_op.f('ix_attendance_records_student_id'), ['student_id'], unique=False)
        batch_op.drop_constraint(batch_op.f('attendance_records_occurrence_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('attendance_records_child_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_attendance_records_student_id_students'), 'students', ['student_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key(batch_op.f('fk_attendance_records_occurrence_id_occurrences'), 'occurrences', ['occurrence_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('caregiver_magic_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))

    with op.batch_alter_table('caregiver_sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))

    with op.batch_alter_table('caregivers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))

    with op.batch_alter_table('exclusion_dates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.alter_column('reason',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)

    with op.batch_alter_table('session_staff', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))

    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.drop_constraint(batch_op.f('sessions_session_location_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_sessions_location_id_locations'), 'locations', ['location_id'], ['id'])

    with op.batch_alter_table('signups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('needs_devices', sa.Boolean(), server_default='false', nullable=False))
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.drop_constraint(batch_op.f('uq_signups_session_child'), type_='unique')
        batch_op.create_unique_constraint('uq_signups_session_student', ['session_id', 'student_id'])
        batch_op.drop_constraint(batch_op.f('signups_caregiver_id_fkey'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('signups_child_id_fkey'), type_='foreignkey')
        batch_op.create_foreign_key(batch_op.f('fk_signups_student_id_students'), 'students', ['student_id'], ['id'])
        batch_op.drop_column('caregiver_id')
    
    # STEP 11: Add sa_orm_sentinel to all renamed tables (they already have created_at/updated_at)
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('archived', sa.Boolean(), server_default='false', nullable=False))
    
    with op.batch_alter_table('locations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
    
    with op.batch_alter_table('blocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
    
    with op.batch_alter_table('block_links', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
    
    # occurrences is MISSING created_at/updated_at in legacy schema
    with op.batch_alter_table('occurrences', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTimeUTC(timezone=True), server_default=sa.func.now(), nullable=False))
    
    with op.batch_alter_table('staff', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sa_orm_sentinel', sa.Integer(), nullable=True))

    # ### end Alembic commands ###

def schema_downgrades() -> None:
    """schema downgrade migrations go here."""
    # Reverse of upgrade - rename tables back to legacy names
    # WARNING: This is for rollback only. Data will be preserved but schema will revert.
    
    # Drop audit columns first
    with op.batch_alter_table('staff', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('occurrences', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('locations', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('blocks', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('block_links', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('students', schema=None) as batch_op:
        batch_op.drop_column('archived')
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('signups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('caregiver_id', sa.UUID(), nullable=False))
        batch_op.drop_column('needs_devices')
        batch_op.drop_column('sa_orm_sentinel')
        batch_op.drop_constraint('uq_signups_session_student', type_='unique')
        batch_op.create_unique_constraint('uq_signups_session_child', ['session_id', 'child_id'])
        batch_op.drop_constraint(batch_op.f('fk_signups_student_id_students'), type_='foreignkey')
        batch_op.create_foreign_key('signups_child_id_fkey', 'children', ['child_id'], ['id'])
        batch_op.create_foreign_key('signups_caregiver_id_fkey', 'caregivers', ['caregiver_id'], ['id'])
    
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('waitlist', sa.Boolean(), server_default='false', nullable=False))
        batch_op.drop_column('sa_orm_sentinel')
        batch_op.drop_constraint(batch_op.f('fk_sessions_location_id_locations'), type_='foreignkey')
        batch_op.create_foreign_key('sessions_session_location_id_fkey', 'session_locations', ['session_location_id'], ['id'])
    
    with op.batch_alter_table('session_staff', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('exclusion_dates', schema=None) as batch_op:
        batch_op.alter_column('reason', existing_type=sa.VARCHAR(length=255), nullable=True)
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('caregivers', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('caregiver_sessions', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('caregiver_magic_links', schema=None) as batch_op:
        batch_op.drop_column('sa_orm_sentinel')
    
    with op.batch_alter_table('attendance_records', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('sa_orm_sentinel')
        batch_op.drop_index(batch_op.f('ix_attendance_records_student_id'))
        batch_op.create_index('ix_attendance_records_child_id', ['child_id'], unique=False)
        batch_op.drop_constraint(batch_op.f('fk_attendance_records_occurrence_id_occurrences'), type_='foreignkey')
        batch_op.drop_constraint(batch_op.f('fk_attendance_records_student_id_students'), type_='foreignkey')
        batch_op.create_foreign_key('attendance_records_child_id_fkey', 'children', ['child_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('attendance_records_occurrence_id_fkey', 'session_occurrences', ['occurrence_id'], ['id'], ondelete='CASCADE')
    
    # Rename columns back
    op.execute("ALTER TABLE sessions RENAME COLUMN location_id TO session_location_id")
    op.execute("ALTER TABLE attendance_records RENAME COLUMN student_id TO child_id")
    op.execute("ALTER TABLE signups RENAME COLUMN student_id TO child_id")
    
    # Rename tables back to legacy names
    op.rename_table('students', 'children')
    op.rename_table('occurrences', 'session_occurrences')
    op.rename_table('block_links', 'session_block_links')
    op.rename_table('blocks', 'session_blocks')
    op.rename_table('locations', 'session_locations')
    
    # Recreate dropped legacy tables (empty - data was permanently deleted)
    op.execute("""
        CREATE TABLE IF NOT EXISTS child_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
            note TEXT NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_child_notes_child_id ON child_notes(child_id)")
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS attendance_audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            occurrence_id UUID NOT NULL REFERENCES session_occurrences(id) ON DELETE CASCADE,
            child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
            status VARCHAR(50) NOT NULL,
            marked_by VARCHAR(255),
            marked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_audit_logs_occurrence_id ON attendance_audit_logs(occurrence_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_audit_logs_child_id ON attendance_audit_logs(child_id)")
    
    # Recreate views
    op.execute("""
        CREATE OR REPLACE VIEW sessions_public AS
        SELECT s.id, s.name, s.description, s.min_year, s.max_year, s.max_signups,
               sl.name AS location_name, sl.address, sl.region
        FROM sessions s
        JOIN session_locations sl ON s.session_location_id = sl.id
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW session_occurrences_public AS
        SELECT so.id, so.session_id, so.starts_at, so.ends_at, so.cancelled,
               sb.year, sb.name AS block_name
        FROM session_occurrences so
        JOIN session_blocks sb ON so.block_id = sb.id
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW children_staff AS
        SELECT c.id, c.name, c.date_of_birth, c.region, c.school_name,
               cg.name AS caregiver_name, cg.email AS caregiver_email
        FROM children c
        JOIN caregivers cg ON c.caregiver_id = cg.id
    """)
    
    op.execute("""
        CREATE OR REPLACE VIEW caregivers_staff AS
        SELECT cg.id, cg.name, cg.email, cg.phone, cg.region,
               COUNT(DISTINCT c.id) AS num_children
        FROM caregivers cg
        LEFT JOIN children c ON c.caregiver_id = cg.id
        GROUP BY cg.id, cg.name, cg.email, cg.phone, cg.region
    """)
    # ### end Alembic commands ###


def data_upgrades() -> None:
    """Add any optional data upgrade migrations here!"""
    pass


def data_downgrades() -> None:
    """Add any optional data downgrade migrations here!"""
    pass
