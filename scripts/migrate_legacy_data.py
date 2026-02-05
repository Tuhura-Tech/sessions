#!/usr/bin/env python3
"""
Data migration script: Legacy schema → Current schema

This script extracts data from backup.sql (legacy format) and transforms it
to match the current application schema, handling:
- Table renames: children → students, session_locations → locations, etc.
- Column renames: child_id → student_id, session_location_id → location_id
- Schema changes: dropping/adding columns as needed

Usage:
    python scripts/migrate_legacy_data.py [backup.sql] [--dry-run]
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass
class ColumnMapping:
    """Mapping for column transformations."""

    legacy_name: str
    current_name: str
    transform: Optional[callable] = None


@dataclass
class TableMapping:
    """Mapping for table transformations."""

    legacy_name: str
    current_name: str
    column_mappings: Dict[str, ColumnMapping]
    columns_to_drop: List[str] = None
    columns_to_add: Dict[str, any] = None
    boolean_columns: List[str] = None

    def __post_init__(self):
        if self.columns_to_drop is None:
            self.columns_to_drop = []
        if self.columns_to_add is None:
            self.columns_to_add = {}
        if self.boolean_columns is None:
            self.boolean_columns = []


class LegacyDataParser:
    """Parser for PostgreSQL COPY format from backup.sql"""

    def __init__(self, backup_file: str):
        self.backup_file = backup_file
        self.tables: Dict[str, Dict] = {}
        self._parse_sql()

    def _parse_sql(self):
        """Extract COPY data from SQL file using line-based parsing."""
        with open(self.backup_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # Look for COPY statement
            match = re.match(r"COPY public\.(\w+)\s*\((.*?)\)\s*FROM stdin;", line)
            if match:
                table_name = match.group(1)
                columns_str = match.group(2)
                columns = [col.strip() for col in columns_str.split(",")]

                # Collect data rows until we hit \.
                rows = []
                i += 1
                while i < len(lines):
                    data_line = lines[i]

                    # Check for end marker
                    if data_line.strip() == r"\.":
                        break

                    # Parse data row
                    if data_line.strip():
                        values = self._parse_row(data_line.rstrip("\n"), columns)
                        if values and len(values) == len(columns):
                            rows.append(dict(zip(columns, values)))

                    i += 1

                self.tables[table_name] = {"columns": columns, "rows": rows}

            i += 1

    def _parse_row(self, line: str, columns: List[str]) -> List[Optional[str]]:
        """Parse a row from COPY data (handling mixed tab/space delimiters)."""
        # Try tab-separated first
        if "\t" in line:
            values = line.split("\t")
        else:
            # Space-separated - need careful parsing
            values = self._parse_space_separated(line, len(columns))

        # Convert empty strings and \N to None
        return [None if v in ("\\N", "") else v for v in values]

    def _parse_space_separated(self, line: str, expected_count: int) -> List[str]:
        """Parse space-separated values, handling quoted strings and special cases."""
        values = []
        current = []
        in_quotes = False

        for char in line:
            if char == '"' and (not current or current[-1] != "\\"):
                in_quotes = not in_quotes
                current.append(char)
            elif char == " " and not in_quotes:
                if current or len(values) < expected_count:
                    values.append("".join(current))
                    current = []
            else:
                current.append(char)

        if current:
            values.append("".join(current))

        # Pad with empty strings if needed
        while len(values) < expected_count:
            values.append("")

        return values[:expected_count]

    def get_table(self, table_name: str) -> Optional[Dict]:
        """Get parsed table data."""
        return self.tables.get(table_name)

    def list_tables(self) -> List[str]:
        """List all extracted tables."""
        return list(self.tables.keys())

    def get_row_count(self, table_name: str) -> int:
        """Get number of rows in a table."""
        table = self.get_table(table_name)
        return len(table["rows"]) if table else 0


class SchemaTransformer:
    """Transform legacy data to current schema."""

    # Define table and column mappings
    TABLE_MAPPINGS = {
        "caregivers": TableMapping(
            legacy_name="caregivers",
            current_name="caregivers",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "name": ColumnMapping("name", "name"),
                "email": ColumnMapping("email", "email"),
                "phone": ColumnMapping("phone", "phone"),
                "email_verified": ColumnMapping("email_verified", "email_verified"),
                "last_login_at": ColumnMapping("last_login_at", "last_login_at"),
                "referral_source": ColumnMapping("referral_source", "referral_source"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
            boolean_columns=["email_verified"],
        ),
        "children": TableMapping(
            legacy_name="children",
            current_name="students",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "caregiver_id": ColumnMapping("caregiver_id", "caregiver_id"),
                "name": ColumnMapping("name", "name"),
                "date_of_birth": ColumnMapping("date_of_birth", "date_of_birth"),
                "media_consent": ColumnMapping("media_consent", "media_consent"),
                "medical_info": ColumnMapping("medical_info", "medical_info"),
                "other_info": ColumnMapping("other_info", "other_info"),
                "region": ColumnMapping("region", "region"),
                "ethnicity": ColumnMapping("ethnicity", "ethnicity"),
                "school_name": ColumnMapping("school_name", "school_name"),
                "gender": ColumnMapping("gender", "gender"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
            columns_to_drop=["needs_devices"],
            columns_to_add={"archived": False},
            boolean_columns=["media_consent", "archived"],
        ),
        "session_locations": TableMapping(
            legacy_name="session_locations",
            current_name="locations",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "name": ColumnMapping("name", "name"),
                "address": ColumnMapping("address", "address"),
                "region": ColumnMapping("region", "region"),
                "lat": ColumnMapping("lat", "lat"),
                "lng": ColumnMapping("lng", "lng"),
                "instructions": ColumnMapping("instructions", "instructions"),
                "contact_name": ColumnMapping("contact_name", "contact_name"),
                "contact_email": ColumnMapping("contact_email", "contact_email"),
                "contact_phone": ColumnMapping("contact_phone", "contact_phone"),
                "internal_notes": ColumnMapping("internal_notes", "internal_notes"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
        "session_blocks": TableMapping(
            legacy_name="session_blocks",
            current_name="blocks",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "year": ColumnMapping("year", "year"),
                "block_type": ColumnMapping("block_type", "block_type"),
                "name": ColumnMapping("name", "name"),
                "start_date": ColumnMapping("start_date", "start_date"),
                "end_date": ColumnMapping("end_date", "end_date"),
                # 'timezone' column dropped - not in current schema
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
        "session_block_links": TableMapping(
            legacy_name="session_block_links",
            current_name="block_links",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "session_id": ColumnMapping("session_id", "session_id"),
                "block_id": ColumnMapping("block_id", "block_id"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
        "session_occurrences": TableMapping(
            legacy_name="session_occurrences",
            current_name="occurrences",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "session_id": ColumnMapping("session_id", "session_id"),
                "starts_at": ColumnMapping("starts_at", "starts_at"),
                "ends_at": ColumnMapping("ends_at", "ends_at"),
                "cancelled": ColumnMapping("cancelled", "cancelled"),
                "cancellation_reason": ColumnMapping(
                    "cancellation_reason", "cancellation_reason"
                ),
                # 'auto_generated' column dropped - not in current schema
                "block_id": ColumnMapping("block_id", "block_id"),
            },
            columns_to_add={
                "created_at": "2026-01-20 00:00:00+00",  # Default timestamp
                "updated_at": "2026-01-20 00:00:00+00",  # Default timestamp
            },
            boolean_columns=["cancelled"],
        ),
        "sessions": TableMapping(
            legacy_name="sessions",
            current_name="sessions",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "session_location_id": ColumnMapping(
                    "session_location_id", "location_id"
                ),
                "year": ColumnMapping("year", "year"),
                "session_type": ColumnMapping("session_type", "session_type"),
                "name": ColumnMapping("name", "name"),
                "age_lower": ColumnMapping("age_lower", "age_lower"),
                "age_upper": ColumnMapping("age_upper", "age_upper"),
                "day_of_week": ColumnMapping("day_of_week", "day_of_week"),
                "start_time": ColumnMapping("start_time", "start_time"),
                "end_time": ColumnMapping("end_time", "end_time"),
                "capacity": ColumnMapping("capacity", "capacity"),
                "what_to_bring": ColumnMapping("what_to_bring", "what_to_bring"),
                "prerequisites": ColumnMapping("prerequisites", "prerequisites"),
                "photo_album_url": ColumnMapping("photo_album_url", "photo_album_url"),
                "internal_notes": ColumnMapping("internal_notes", "internal_notes"),
                "archived": ColumnMapping("archived", "archived"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
            columns_to_drop=["waitlist", "capacity_notes"],
            boolean_columns=["archived"],
        ),
        "signups": TableMapping(
            legacy_name="signups",
            current_name="signups",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "session_id": ColumnMapping("session_id", "session_id"),
                "child_id": ColumnMapping("child_id", "student_id"),
                "status": ColumnMapping("status", "status"),
                "withdrawn_at": ColumnMapping("withdrawn_at", "withdrawn_at"),
                "pickup_dropoff": ColumnMapping("pickup_dropoff", "pickup_dropoff"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
            columns_to_drop=["caregiver_id"],
            columns_to_add={"needs_devices": False},
            boolean_columns=["needs_devices"],
        ),
        "staff": TableMapping(
            legacy_name="staff",
            current_name="staff",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "name": ColumnMapping("name", "name"),
                "email": ColumnMapping("email", "email"),
                "sso_id": ColumnMapping("sso_id", "sso_id"),
                "last_login_at": ColumnMapping("last_login_at", "last_login_at"),
                "active": ColumnMapping("active", "active"),
                "deactivated_at": ColumnMapping("deactivated_at", "deactivated_at"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
            boolean_columns=["active"],
        ),
        "session_staff": TableMapping(
            legacy_name="session_staff",
            current_name="session_staff",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "session_id": ColumnMapping("session_id", "session_id"),
                "staff_id": ColumnMapping("staff_id", "staff_id"),
                "assigned_at": ColumnMapping("assigned_at", "assigned_at"),
            },
            columns_to_add={
                "created_at": "2026-01-20 00:00:00+00",
                "updated_at": "2026-01-20 00:00:00+00",
            },
        ),
        "attendance_records": TableMapping(
            legacy_name="attendance_records",
            current_name="attendance_records",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "occurrence_id": ColumnMapping("occurrence_id", "occurrence_id"),
                "child_id": ColumnMapping("child_id", "student_id"),
                "status": ColumnMapping("status", "status"),
                "reason": ColumnMapping("reason", "reason"),
            },
        ),
        "attendance_audit_logs": TableMapping(
            legacy_name="attendance_audit_logs",
            current_name="attendance_audit_logs",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "occurrence_id": ColumnMapping("occurrence_id", "occurrence_id"),
                "child_id": ColumnMapping("child_id", "student_id"),
                "actor": ColumnMapping("actor", "actor"),
                "old_status": ColumnMapping("old_status", "old_status"),
                "new_status": ColumnMapping("new_status", "new_status"),
                "old_reason": ColumnMapping("old_reason", "old_reason"),
                "new_reason": ColumnMapping("new_reason", "new_reason"),
                "changed_at": ColumnMapping("changed_at", "changed_at"),
            },
        ),
        "exclusion_dates": TableMapping(
            legacy_name="exclusion_dates",
            current_name="exclusion_dates",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "year": ColumnMapping("year", "year"),
                "date": ColumnMapping("date", "date"),
                "reason": ColumnMapping("reason", "reason"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
        "caregiver_magic_links": TableMapping(
            legacy_name="caregiver_magic_links",
            current_name="caregiver_magic_links",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "caregiver_id": ColumnMapping("caregiver_id", "caregiver_id"),
                "token_hash": ColumnMapping("token_hash", "token_hash"),
                "expires_at": ColumnMapping("expires_at", "expires_at"),
                "used_at": ColumnMapping("used_at", "used_at"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
        "caregiver_sessions": TableMapping(
            legacy_name="caregiver_sessions",
            current_name="caregiver_sessions",
            column_mappings={
                "id": ColumnMapping("id", "id"),
                "caregiver_id": ColumnMapping("caregiver_id", "caregiver_id"),
                "token_hash": ColumnMapping("token_hash", "token_hash"),
                "expires_at": ColumnMapping("expires_at", "expires_at"),
                "revoked_at": ColumnMapping("revoked_at", "revoked_at"),
                "user_agent": ColumnMapping("user_agent", "user_agent"),
                "ip_address": ColumnMapping("ip_address", "ip_address"),
                "created_at": ColumnMapping("created_at", "created_at"),
                "updated_at": ColumnMapping("updated_at", "updated_at"),
            },
        ),
    }

    LOAD_ORDER = [
        "caregivers",
        "students",
        "locations",
        "blocks",
        "sessions",
        "block_links",
        "occurrences",
        "staff",
        "session_staff",
        "signups",
        "attendance_records",
        "exclusion_dates",
        "caregiver_magic_links",
        "caregiver_sessions",
    ]

    def transform(self, legacy_data: Dict, table_name: str) -> Tuple[str, List[Dict]]:
        """Transform legacy table data to current schema.

        Returns:
            Tuple of (current_table_name, transformed_rows)
        """
        if table_name not in self.TABLE_MAPPINGS:
            # No transformation needed
            return table_name, legacy_data["rows"]

        mapping = self.TABLE_MAPPINGS[table_name]
        transformed_rows = []

        for row in legacy_data["rows"]:
            transformed_row = {}

            # Map columns
            for legacy_col, legacy_value in row.items():
                if legacy_col in mapping.column_mappings:
                    col_mapping = mapping.column_mappings[legacy_col]
                    current_col = col_mapping.current_name

                    # Apply transformation if defined
                    if col_mapping.transform:
                        value = col_mapping.transform(legacy_value)
                    else:
                        value = legacy_value

                    transformed_row[current_col] = value

            # Add default values for new columns
            for col_name, default_value in mapping.columns_to_add.items():
                if col_name not in transformed_row:
                    transformed_row[col_name] = default_value

            transformed_row = self._post_process(mapping.current_name, transformed_row)
            transformed_rows.append(transformed_row)

        return mapping.current_name, transformed_rows

    def _post_process(self, table_name: str, row: Dict) -> Dict:
        """Apply table-specific defaults for required fields."""
        if table_name == "caregivers":
            if not row.get("name"):
                email = row.get("email")
                row["name"] = email or "Unknown caregiver"
        return row

    def transform_all(self, parser_obj: "LegacyDataParser") -> Dict[str, List[Dict]]:
        """Transform all legacy tables into a dict keyed by current table name."""
        transformed: Dict[str, List[Dict]] = {}
        for legacy_table in parser_obj.list_tables():
            legacy_data = parser_obj.get_table(legacy_table)
            if not legacy_data:
                continue
            current_table, rows = self.transform(legacy_data, legacy_table)
            if current_table not in transformed:
                transformed[current_table] = []
            transformed[current_table].extend(rows)
        return transformed

    def ordered_tables(self, tables: Iterable[str]) -> List[str]:
        """Return tables ordered by dependency-safe load order."""
        table_set = set(tables)
        ordered = [t for t in self.LOAD_ORDER if t in table_set]
        remaining = sorted(table_set - set(ordered))
        return ordered + remaining


@dataclass
class ValidationIssue:
    table: str
    message: str


class MigrationValidator:
    """Validate transformed data before loading into the database."""

    REQUIRED_COLUMNS = {
        "caregivers": ["id", "name", "email"],
        "students": ["id", "caregiver_id", "name", "date_of_birth"],
        "locations": ["id", "name", "address"],
        "blocks": ["id", "year", "block_type", "name", "start_date", "end_date"],
        "sessions": [
            "id",
            "location_id",
            "year",
            "session_type",
            "name",
            "age_lower",
            "age_upper",
            "start_time",
            "end_time",
            "capacity",
        ],
        "block_links": ["id", "session_id", "block_id"],
        "occurrences": ["id", "session_id", "block_id", "starts_at", "ends_at"],
        "signups": ["id", "session_id", "student_id", "status"],
        "attendance_records": ["id", "occurrence_id", "student_id", "status"],
        "session_staff": ["id", "session_id", "staff_id"],
        "staff": ["id", "name", "email"],
        "exclusion_dates": ["id", "year", "date"],
        "caregiver_magic_links": ["id", "caregiver_id", "token_hash"],
        "caregiver_sessions": ["id", "caregiver_id", "token_hash"],
    }

    def __init__(self, tables: Dict[str, List[Dict]]):
        self.tables = tables

    def validate(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        issues.extend(self._validate_required_fields())
        issues.extend(self._validate_foreign_keys())
        return issues

    def _validate_required_fields(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        for table, required_cols in self.REQUIRED_COLUMNS.items():
            rows = self.tables.get(table, [])
            for idx, row in enumerate(rows):
                missing = [
                    col
                    for col in required_cols
                    if col not in row or row.get(col) in (None, "")
                ]
                if missing:
                    issues.append(
                        ValidationIssue(
                            table,
                            f"Row {idx + 1} missing required fields: {', '.join(missing)}",
                        )
                    )
        return issues

    def _validate_foreign_keys(self) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        id_sets = {
            table: {row.get("id") for row in rows if row.get("id")}
            for table, rows in self.tables.items()
        }

        def check_fk(
            table: str, column: str, target_table: str, max_examples: int = 5
        ) -> None:
            rows = self.tables.get(table, [])
            target_ids = id_sets.get(target_table, set())
            missing = []
            for row in rows:
                value = row.get(column)
                if value and value not in target_ids:
                    missing.append(value)
                    if len(missing) >= max_examples:
                        break
            if missing:
                issues.append(
                    ValidationIssue(
                        table,
                        f"{column} references missing {target_table} IDs: {', '.join(missing)}",
                    )
                )

        check_fk("students", "caregiver_id", "caregivers")
        check_fk("sessions", "location_id", "locations")
        check_fk("block_links", "session_id", "sessions")
        check_fk("block_links", "block_id", "blocks")
        check_fk("occurrences", "session_id", "sessions")
        check_fk("occurrences", "block_id", "blocks")
        check_fk("signups", "session_id", "sessions")
        check_fk("signups", "student_id", "students")
        check_fk("attendance_records", "occurrence_id", "occurrences")
        check_fk("attendance_records", "student_id", "students")
        check_fk("session_staff", "session_id", "sessions")
        check_fk("session_staff", "staff_id", "staff")
        check_fk("caregiver_magic_links", "caregiver_id", "caregivers")
        check_fk("caregiver_sessions", "caregiver_id", "caregivers")
        return issues


class DataLoader:
    """Load transformed data into PostgreSQL using psql."""

    def __init__(self, use_docker: bool = True):
        self.use_docker = use_docker
        self.sql_buffer = []

    def connect(self):
        """Prepare for data loading."""
        self.sql_buffer = ["BEGIN TRANSACTION;"]
        self.sql_buffer.append("SET session_replication_role = REPLICA;")

    def disconnect(self):
        """Close connection and execute buffered SQL."""
        self.sql_buffer.append("SET session_replication_role = DEFAULT;")
        self.sql_buffer.append("COMMIT;")

    def load_data(
        self,
        table_name: str,
        rows: List[Dict],
        dry_run: bool = False,
        boolean_columns: List[str] = None,
    ) -> int:
        """Buffer rows to be inserted into a table.

        Args:
            table_name: Name of the table to insert into
            rows: List of row dicts to insert
            dry_run: If True, print SQL instead of buffering
            boolean_columns: List of column names that are booleans

        Returns:
            Number of rows to be inserted
        """
        if not rows:
            return 0

        if boolean_columns is None:
            boolean_columns = []

        # Get column names from first row
        columns = list(rows[0].keys())
        col_str = ", ".join(columns)

        for row in rows:
            values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    values.append("NULL")
                elif isinstance(val, bool):
                    values.append("true" if val else "false")
                elif isinstance(val, str):
                    # Only convert to boolean if this is a boolean column
                    if col in boolean_columns:
                        if val.lower() in ("t", "true", "yes", "on", "1"):
                            values.append("true")
                        elif val.lower() in ("f", "false", "no", "off", "0"):
                            values.append("false")
                        else:
                            # Not a valid boolean - escape as string
                            escaped = val.replace("'", "''")
                            values.append(f"'{escaped}'")
                    else:
                        # Regular string - escape single quotes
                        escaped = val.replace("'", "''")
                        values.append(f"'{escaped}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    # Escape single quotes
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")

            values_str = ", ".join(values)
            insert_sql = f"INSERT INTO {table_name} ({col_str}) VALUES ({values_str});"

            if dry_run:
                print(insert_sql)
            else:
                self.sql_buffer.append(insert_sql)

        return len(rows)

    def execute(self, dry_run: bool = False):
        """Execute all buffered SQL commands."""
        if dry_run:
            return True  # Already printed above

        sql_script = "\n".join(self.sql_buffer)

        if self.use_docker:
            import os
            import subprocess

            # Create temp file in /tmp with proper permissions
            temp_file = f"/tmp/migrate_{os.getpid()}.sql"

            try:
                # Write SQL to file
                with open(temp_file, "w") as f:
                    f.write(sql_script)

                # Execute via docker compose from the project directory
                result = subprocess.run(
                    f"cd /home/leon/Projects/sessions && cat {temp_file} | docker compose exec -T postgres psql -U sessions -d sessions",
                    shell=True,
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    print(f"ERROR executing SQL: {result.stderr}", file=sys.stderr)
                    if result.stdout:
                        print(f"Output: {result.stdout}", file=sys.stderr)
                    return False

                # Check for errors in output (PostgreSQL error lines start with "ERROR:")
                for line in result.stdout.split("\n") + result.stderr.split("\n"):
                    if line.startswith("ERROR:"):
                        print("WARNING: SQL error detected:", file=sys.stderr)
                        print(result.stdout, file=sys.stderr)
                        print(result.stderr, file=sys.stderr)
                        return False

                return True
            finally:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        return False

    def fetch_row_counts(self, tables: Iterable[str]) -> Dict[str, int]:
        """Fetch row counts from the database for the given tables."""
        if not self.use_docker:
            return {}

        import subprocess

        counts: Dict[str, int] = {}
        for table in tables:
            result = subprocess.run(
                f'cd /home/leon/Projects/sessions && docker compose exec -T postgres psql -U sessions -d sessions -t -A -c "SELECT COUNT(*) FROM {table};"',
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(
                    f"ERROR fetching count for {table}: {result.stderr}",
                    file=sys.stderr,
                )
                continue
            output = result.stdout.strip()
            try:
                counts[table] = int(output)
            except ValueError:
                print(
                    f"WARNING: Could not parse row count for {table}: {output}",
                    file=sys.stderr,
                )
        return counts


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy database data to current schema"
    )
    parser.add_argument(
        "backup_file",
        nargs="?",
        default="backup.sql",
        help="Path to backup.sql file (default: backup.sql)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying database",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation checks before loading data",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation only (no data loaded)",
    )
    args = parser.parse_args()

    # Check backup file exists
    if not Path(args.backup_file).exists():
        print(f"Error: backup file not found: {args.backup_file}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading legacy data from: {args.backup_file}")
    print()

    # Parse legacy data
    print("Parsing legacy data...")
    parser_obj = LegacyDataParser(args.backup_file)
    print(f"Found {len(parser_obj.list_tables())} tables")
    print()

    # Show what will be migrated
    print("Data to migrate:")
    for table in sorted(parser_obj.list_tables()):
        count = parser_obj.get_row_count(table)
        print(f"  {table}: {count} rows")
    print()

    if args.dry_run:
        print("DRY RUN MODE - no changes will be made")
        print()

    # Transform and load data
    transformer = SchemaTransformer()
    loader = DataLoader(use_docker=True)

    # Tables that don't exist in current schema
    TABLES_TO_SKIP = {"alembic_version", "attendance_audit_logs", "child_notes"}

    try:
        # Transform and merge all tables first
        transformed_tables = transformer.transform_all(parser_obj)

        # Remove tables that don't exist in current schema
        for skipped in TABLES_TO_SKIP:
            if skipped in transformed_tables:
                del transformed_tables[skipped]

        if not args.skip_validation:
            print("Running validation checks...")
            validator = MigrationValidator(transformed_tables)
            issues = validator.validate()
            if issues:
                print("Validation failed:")
                for issue in issues:
                    print(f"  - {issue.table}: {issue.message}")
                print("\nFix the data issues or re-run with --skip-validation.")
                sys.exit(1)
            print("✓ Validation checks passed")
            print()

        if args.validate_only:
            print("Validation-only mode complete (no data loaded).")
            return

        loader.connect()

        total_loaded = 0
        ordered_tables = transformer.ordered_tables(transformed_tables.keys())
        for current_table in ordered_tables:
            transformed_rows = transformed_tables.get(current_table, [])
            if not transformed_rows:
                print(f"  {current_table}: skipped (no rows)")
                continue

            legacy_table = next(
                (
                    legacy
                    for legacy, mapping in transformer.TABLE_MAPPINGS.items()
                    if mapping.current_name == current_table
                ),
                current_table,
            )
            mapping = transformer.TABLE_MAPPINGS.get(legacy_table)
            boolean_cols = mapping.boolean_columns if mapping else []

            count = loader.load_data(
                current_table, transformed_rows, args.dry_run, boolean_cols
            )
            total_loaded += count
            status = "DRY RUN" if args.dry_run else "BUFFERED"
            print(f"✓ {legacy_table} → {current_table}: {count} rows {status}")

        # Execute buffered SQL
        loader.disconnect()
        if not args.dry_run:
            success = loader.execute(args.dry_run)
            if success:
                print()
                print(f"Total rows loaded: {total_loaded}")

                # Verify row counts in the database
                print("Validating database row counts...")
                expected_counts = {
                    table: len(rows)
                    for table, rows in transformed_tables.items()
                    if rows
                }
                actual_counts = loader.fetch_row_counts(expected_counts.keys())
                mismatches = []
                for table, expected in expected_counts.items():
                    actual = actual_counts.get(table)
                    if actual is None:
                        mismatches.append(f"{table}: expected {expected}, got N/A")
                    elif actual != expected:
                        mismatches.append(f"{table}: expected {expected}, got {actual}")

                if mismatches:
                    print("✗ Row count validation failed:")
                    for mismatch in mismatches:
                        print(f"  - {mismatch}")
                    sys.exit(1)

                print("✓ Migration complete and validated!")
            else:
                print("✗ Migration failed during execution")
                sys.exit(1)
        else:
            print()
            print(f"Total rows to load: {total_loaded}")
            print("(DRY RUN - run without --dry-run to actually load data)")

    except Exception as e:
        print(f"Error during migration: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
