from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.lib.schema import CamelizedBaseSchema


class AttendanceStats(CamelizedBaseSchema):
    """Attendance statistics for a session."""

    session_id: UUID
    total_occurrences: int
    total_students: int
    average_attendance_rate: float

    students_with_perfect_attendance: int
    students_with_good_attendance: int  # >80%
    students_with_poor_attendance: int  # <50%

    best_attended_occurrence: OccurrenceAttendanceSummary | None = None
    worst_attended_occurrence: OccurrenceAttendanceSummary | None = None


class OccurrenceAttendanceSummary(CamelizedBaseSchema):
    """Summary of attendance for a single occurrence."""

    occurrence_id: UUID
    date: datetime
    total_students: int
    present_count: int
    absent_known_count: int
    absent_unknown_count: int
    attendance_rate: float


class StudentAttendanceSummary(CamelizedBaseSchema):
    """Attendance summary for a student."""

    student_id: UUID
    student_name: str
    total_occurrences: int
    present_count: int
    absent_known_count: int
    absent_unknown_count: int
    attendance_rate: float
    is_at_risk: bool  # attendance_rate < 0.5
