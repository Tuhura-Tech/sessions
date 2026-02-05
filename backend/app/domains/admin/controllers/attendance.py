from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers
from litestar import Controller, get, post
from litestar.di import Provide
from litestar.exceptions import NotFoundException, ValidationException
from sqlalchemy.orm import selectinload

from app.db import models as m
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.schemas.attendance import (
    AttendanceRecord,
    AttendanceRoll,
    AttendanceRollItem,
    AttendanceUpsert,
)
from app.domains.admin.schemas.attendance_stats import (
    AttendanceStats,
    OccurrenceAttendanceSummary,
    StudentAttendanceSummary,
)
from app.domains.admin.services.attendance import AttendanceService
from app.domains.admin.services.occurrences import OccurrenceService
from app.domains.admin.services.signup import SignupService


class AttendanceController(Controller):
    """Admin endpoints for managing attendance."""

    path = "/api/v1/admin/occurrences/{occurrence_id:uuid}"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = {
        "attendance_service": Provide(
            providers.create_service_provider(AttendanceService)
        ),
        "occurrence_service": Provide(
            providers.create_service_provider(OccurrenceService)
        ),
        "signup_service": Provide(providers.create_service_provider(SignupService)),
    }

    @get("/roll")
    async def get_attendance_roll(
        self,
        occurrence_id: UUID,
        occurrence_service: OccurrenceService,
        signup_service: SignupService,
        attendance_service: AttendanceService,
    ) -> AttendanceRoll:
        """Get the attendance roll for an occurrence.

        Returns all students signed up for the session with their current
        attendance status for this occurrence.
        """
        occurrence = await occurrence_service.get(
            occurrence_id, load=[selectinload(m.Occurrence.session)]
        )
        if not occurrence:
            raise NotFoundException(detail="Occurrence not found")

        # Get all data in single query with joins
        signups = await signup_service.list(
            m.Signup.session_id == occurrence.session_id,
            m.Signup.status.in_(["confirmed", "waitlisted"]),
            load=[
                selectinload(m.Signup.student).selectinload(m.Student.caregiver),
            ],
        )

        # Get attendance records for this occurrence
        attendance_records = await attendance_service.list(
            occurrence_id=occurrence_id,
        )

        # Create lookup dict
        attendance_by_student = {
            record.student_id: attendance_service.to_schema(
                record, schema_type=AttendanceRecord
            )
            for record in attendance_records
        }

        # Build roll items
        items = [
            AttendanceRollItem(
                signup_id=signup.id,
                student_id=signup.student_id,
                student_name=signup.student.name,
                caregiver_name=signup.student.caregiver.name or "",
                attendance=attendance_by_student.get(signup.student_id),
            )
            for signup in signups
        ]

        return AttendanceRoll(
            occurrence_id=occurrence.id,
            session_id=occurrence.session_id,
            starts_at=occurrence.starts_at,
            ends_at=occurrence.ends_at,
            cancelled=occurrence.cancelled,
            items=items,
        )

    @post("/attendance")
    async def upsert_attendance(
        self,
        occurrence_id: UUID,
        data: list[AttendanceUpsert],
        occurrence_service: OccurrenceService,
        attendance_service: AttendanceService,
        signup_service: SignupService,
    ) -> list[AttendanceRecord]:
        """Mark or update attendance for multiple students in a single transaction.

        Creates new attendance records or updates existing ones. Validates that
        all students have active signups and that the occurrence is not cancelled.
        """
        # Validate input not empty
        if not data:
            raise ValidationException(detail="Attendance data cannot be empty")

        # Get occurrence with validation
        occurrence = await occurrence_service.get(occurrence_id)
        if not occurrence:
            raise NotFoundException(detail="Occurrence not found")

        # Block attendance on cancelled occurrences
        if occurrence.cancelled:
            raise ValidationException(
                detail="Cannot mark attendance for cancelled occurrence. "
                "Please reinstate the occurrence first."
            )

        # Get valid signups for validation
        signups = await signup_service.list(
            session_id=occurrence.session_id,
            status=["confirmed", "waitlisted"],
        )
        valid_student_ids = {signup.student_id for signup in signups}

        # Validate all students belong to session and have active signups
        for item in data:
            if item.student_id not in valid_student_ids:
                raise ValidationException(
                    detail=f"Student {item.student_id} is not actively "
                    "signed up for this session. "
                    "Status must be 'confirmed' or 'waitlisted'."
                )

        # Use transaction for atomicity
        async with attendance_service.repository.session.begin_nested():
            # Get existing attendance records
            existing_records = await attendance_service.list(
                occurrence_id=occurrence_id
            )
            existing_by_student = {
                record.student_id: record for record in existing_records
            }

            results = []
            for item in data:
                existing = existing_by_student.get(item.student_id)

                if existing:
                    # Update existing record
                    updated = await attendance_service.update(
                        {
                            "status": item.status,
                            "reason": item.reason,
                        },
                        existing.id,
                    )
                    results.append(
                        attendance_service.to_schema(
                            updated, schema_type=AttendanceRecord
                        )
                    )
                else:
                    # Create new record
                    created = await attendance_service.create(
                        {
                            "occurrence_id": occurrence_id,
                            "student_id": item.student_id,
                            "status": item.status,
                            "reason": item.reason,
                        }
                    )
                    results.append(
                        attendance_service.to_schema(
                            created, schema_type=AttendanceRecord
                        )
                    )

        return results

    @get("/attendance-history")
    async def get_attendance_history(
        self,
        occurrence_id: UUID,
        occurrence_service: OccurrenceService,
        attendance_service: AttendanceService,
    ) -> list[AttendanceRecord]:
        """Get the complete attendance history for an occurrence.

        Returns all attendance records with their full audit trail.
        This is useful for reviewing past changes and attendance patterns.

        Returns all attendance records for a specific occurrence.
        """
        records = await attendance_service.list(occurrence_id=occurrence_id)

        return [
            attendance_service.to_schema(record, schema_type=AttendanceRecord)
            for record in records
        ]


class AttendanceStatsController(Controller):
    """Admin endpoints for attendance statistics and analytics."""

    path = "/api/v1/admin/sessions/{session_id:uuid}/attendance"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = {
        "attendance_service": Provide(
            providers.create_service_provider(AttendanceService)
        ),
        "occurrence_service": Provide(
            providers.create_service_provider(OccurrenceService)
        ),
        "signup_service": Provide(providers.create_service_provider(SignupService)),
    }

    @get("/stats")
    async def get_attendance_stats(
        self,
        session_id: UUID,
        occurrence_service: OccurrenceService,
        attendance_service: AttendanceService,
        signup_service: SignupService,
    ) -> AttendanceStats:
        """Get comprehensive attendance statistics for a session.

        Provides overall metrics, per-occurrence breakdown, and per-student summaries.
        """
        # Get all occurrences for this session
        occurrences = await occurrence_service.list(session_id=session_id)

        if not occurrences:
            return AttendanceStats(
                session_id=session_id,
                total_occurrences=0,
                total_students=0,
                average_attendance_rate=0.0,
                students_with_perfect_attendance=0,
                students_with_good_attendance=0,
                students_with_poor_attendance=0,
                best_attended_occurrence=None,
                worst_attended_occurrence=None,
            )

        occurrence_ids = [occ.id for occ in occurrences]

        # Get all attendance in one query
        all_attendance = await attendance_service.list(
            m.AttendanceRecord.occurrence_id.in_(occurrence_ids),
            load=[selectinload(m.AttendanceRecord.student)],
        )

        # Get all signups
        signups = await signup_service.list(
            session_id=session_id,
            status=["confirmed", "waitlisted"],
        )
        total_students = len(signups)

        # Calculate per-occurrence stats
        occurrence_stats = []
        for occurrence in occurrences:
            occ_attendance = [
                a for a in all_attendance if a.occurrence_id == occurrence.id
            ]
            present = sum(1 for a in occ_attendance if a.status == "present")
            absent_known = sum(1 for a in occ_attendance if a.status == "absent_known")
            absent_unknown = sum(
                1 for a in occ_attendance if a.status == "absent_unknown"
            )

            rate = present / total_students if total_students > 0 else 0.0

            occurrence_stats.append(
                OccurrenceAttendanceSummary(
                    occurrence_id=occurrence.id,
                    date=occurrence.starts_at,
                    total_students=total_students,
                    present_count=present,
                    absent_known_count=absent_known,
                    absent_unknown_count=absent_unknown,
                    attendance_rate=rate,
                )
            )

        # Calculate per-student stats
        student_attendance = defaultdict(lambda: {"present": 0, "total": 0})
        for attendance in all_attendance:
            student_attendance[attendance.student_id]["total"] += 1
            if attendance.status == "present":
                student_attendance[attendance.student_id]["present"] += 1

        perfect = good = poor = 0
        for stats in student_attendance.values():
            if stats["total"] == 0:
                continue
            rate = stats["present"] / stats["total"]
            if rate == 1.0:
                perfect += 1
            elif rate > 0.8:
                good += 1
            elif rate < 0.5:
                poor += 1

        # Overall average
        total_possible = len(occurrences) * total_students
        total_present = sum(1 for a in all_attendance if a.status == "present")
        avg_rate = total_present / total_possible if total_possible > 0 else 0.0

        # Best and worst occurrences
        best = max(occurrence_stats, key=lambda x: x.attendance_rate, default=None)
        worst = min(occurrence_stats, key=lambda x: x.attendance_rate, default=None)

        return AttendanceStats(
            session_id=session_id,
            total_occurrences=len(occurrences),
            total_students=total_students,
            average_attendance_rate=avg_rate,
            students_with_perfect_attendance=perfect,
            students_with_good_attendance=good,
            students_with_poor_attendance=poor,
            best_attended_occurrence=best,
            worst_attended_occurrence=worst,
        )

    @get("/at-risk")
    async def get_at_risk_students(
        self,
        session_id: UUID,
        occurrence_service: OccurrenceService,
        attendance_service: AttendanceService,
        signup_service: SignupService,
        threshold: float = 0.7,
    ) -> list[StudentAttendanceSummary]:
        """Get students with attendance below the specified threshold.

        Identifies students who may need intervention based on low attendance.
        Default threshold is 70% attendance rate.
        """
        occurrences = await occurrence_service.list(session_id=session_id)

        if not occurrences:
            return []

        occurrence_ids = [occ.id for occ in occurrences]
        all_attendance = await attendance_service.list(
            m.AttendanceRecord.occurrence_id.in_(occurrence_ids),
            load=[selectinload(m.AttendanceRecord.student)],
        )

        signups = await signup_service.list(
            session_id=session_id,
            status=["confirmed", "waitlisted"],
            load=[selectinload(m.Signup.student)],
        )

        # Calculate per-student attendance
        student_stats = {}
        for signup in signups:
            student_attendance = [
                a for a in all_attendance if a.student_id == signup.student_id
            ]

            present = sum(1 for a in student_attendance if a.status == "present")
            absent_known = sum(
                1 for a in student_attendance if a.status == "absent_known"
            )
            absent_unknown = sum(
                1 for a in student_attendance if a.status == "absent_unknown"
            )

            total_marked = len(student_attendance)
            rate = present / total_marked if total_marked > 0 else 0.0

            if rate < threshold:
                student_stats[signup.student_id] = StudentAttendanceSummary(
                    student_id=signup.student_id,
                    student_name=signup.student.name,
                    total_occurrences=len(occurrences),
                    present_count=present,
                    absent_known_count=absent_known,
                    absent_unknown_count=absent_unknown,
                    attendance_rate=rate,
                    is_at_risk=True,
                )

        return list(student_stats.values())
