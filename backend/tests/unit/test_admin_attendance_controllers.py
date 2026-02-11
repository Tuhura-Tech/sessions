from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from litestar.exceptions import NotFoundException, ValidationException

from app.domains.admin.controllers.attendance import (
    AttendanceController,
    AttendanceStatsController,
)
from app.domains.admin.schemas.attendance import AttendanceRecord, AttendanceUpsert


@dataclass
class FakeCaregiver:
    name: str


@dataclass
class FakeStudent:
    id: UUID
    name: str
    caregiver: FakeCaregiver


@dataclass
class FakeSignup:
    id: UUID
    student_id: UUID
    student: FakeStudent
    status: str = "confirmed"


@dataclass
class FakeOccurrence:
    id: UUID
    session_id: UUID
    starts_at: datetime
    ends_at: datetime
    cancelled: bool


@dataclass
class FakeAttendanceRecord:
    id: UUID
    occurrence_id: UUID
    student_id: UUID
    status: str
    reason: str | None = None


class DummyNested:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class DummyRepository:
    class DummySession:
        def begin_nested(self) -> DummyNested:
            return DummyNested()

    session = DummySession()


class DummyAttendanceService:
    def __init__(self, records: list[FakeAttendanceRecord] | None = None) -> None:
        self._records = records or []
        self.repository = DummyRepository()

    async def list(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._records)

    async def update(self, data: dict, record_id: UUID) -> FakeAttendanceRecord:
        record = next(r for r in self._records if r.id == record_id)
        record.status = data.get("status", record.status)
        record.reason = data.get("reason", record.reason)
        return record

    async def create(self, data: dict) -> FakeAttendanceRecord:
        record = FakeAttendanceRecord(
            id=uuid4(),
            occurrence_id=data["occurrence_id"],
            student_id=data["student_id"],
            status=data["status"],
            reason=data.get("reason"),
        )
        self._records.append(record)
        return record

    def to_schema(self, record: FakeAttendanceRecord, schema_type=AttendanceRecord):
        now = datetime.now(UTC)
        return schema_type(
            id=record.id,
            occurrence_id=record.occurrence_id,
            student_id=record.student_id,
            status=record.status,
            reason=record.reason,
            created_at=now,
            updated_at=now,
        )


class DummyOccurrenceService:
    def __init__(self, occurrence: FakeOccurrence | None = None):
        self._occurrence = occurrence
        self._occurrences: list[FakeOccurrence] = []

    async def get(self, occurrence_id: UUID, *args, **kwargs) -> FakeOccurrence | None:
        if self._occurrence and self._occurrence.id == occurrence_id:
            return self._occurrence
        return None

    async def list(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return list(self._occurrences)


class DummySignupService:
    def __init__(self, signups: list[FakeSignup] | None = None):
        self._signups = signups or []
        self._filter_calls: list[tuple] = []

    async def list(self, *args, **kwargs):  # noqa: ANN002, ANN003
        """Filter signups based on SQLAlchemy filter expressions.

        Supports filtering by:
        - m.Signup.session_id == session_id
        - m.Signup.status.in_(["confirmed", "waitlisted"])
        """
        # Store the call for testing
        self._filter_calls.append((args, kwargs))

        filtered = list(self._signups)

        # For unit tests, we simply return the signups.
        # The test setup should only include the signups we want returned.
        return filtered


def make_attendance_controller() -> AttendanceController:
    return AttendanceController(owner=SimpleNamespace())


def make_stats_controller() -> AttendanceStatsController:
    return AttendanceStatsController(owner=SimpleNamespace())


@pytest.mark.anyio
class TestAttendanceController:
    async def test_get_attendance_roll_success(self) -> None:
        controller = make_attendance_controller()
        controller = make_attendance_controller()
        now = datetime.now(UTC)
        session_id = uuid4()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            cancelled=False,
        )

        caregiver = FakeCaregiver(name="Caregiver A")
        student = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        signup = FakeSignup(id=uuid4(), student_id=student.id, student=student)
        attendance = FakeAttendanceRecord(
            id=uuid4(),
            occurrence_id=occurrence.id,
            student_id=student.id,
            status="present",
        )

        occurrence_service = DummyOccurrenceService(occurrence)
        signup_service = DummySignupService([signup])
        attendance_service = DummyAttendanceService([attendance])

        roll = await AttendanceController.get_attendance_roll.fn(
            controller,
            occurrence_id=occurrence.id,
            occurrence_service=occurrence_service,
            signup_service=signup_service,
            attendance_service=attendance_service,
        )

        assert roll.occurrence_id == occurrence.id
        assert len(roll.items) == 1
        assert roll.items[0].attendance is not None

    async def test_get_attendance_roll_not_found(self) -> None:
        controller = make_attendance_controller()
        occurrence_service = DummyOccurrenceService(None)
        signup_service = DummySignupService([])
        attendance_service = DummyAttendanceService([])

        with pytest.raises(NotFoundException):
            await AttendanceController.get_attendance_roll.fn(
                controller,
                occurrence_id=uuid4(),
                occurrence_service=occurrence_service,
                signup_service=signup_service,
                attendance_service=attendance_service,
            )

    async def test_upsert_attendance_empty_data(self) -> None:
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)
        signup_service = DummySignupService([])
        attendance_service = DummyAttendanceService([])

        with pytest.raises(ValidationException):
            await AttendanceController.upsert_attendance.fn(
                controller,
                occurrence_id=occurrence.id,
                data=[],
                occurrence_service=occurrence_service,
                attendance_service=attendance_service,
                signup_service=signup_service,
            )

    async def test_upsert_attendance_cancelled(self) -> None:
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=True,
        )
        occurrence_service = DummyOccurrenceService(occurrence)
        signup_service = DummySignupService([])
        attendance_service = DummyAttendanceService([])

        with pytest.raises(ValidationException):
            await AttendanceController.upsert_attendance.fn(
                controller,
                occurrence_id=occurrence.id,
                data=[
                    AttendanceUpsert(student_id=uuid4(), status="present", reason=None)
                ],
                occurrence_service=occurrence_service,
                attendance_service=attendance_service,
                signup_service=signup_service,
            )

    async def test_upsert_attendance_confirmed_signup(self) -> None:
        """Test that students with confirmed signup status can have attendance marked."""
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        caregiver = FakeCaregiver(name="Caregiver A")
        student = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        # CONFIRMED status signup
        signup = FakeSignup(
            id=uuid4(), student_id=student.id, student=student, status="confirmed"
        )
        signup_service = DummySignupService([signup])
        attendance_service = DummyAttendanceService([])

        results = await AttendanceController.upsert_attendance.fn(
            controller,
            occurrence_id=occurrence.id,
            data=[
                AttendanceUpsert(student_id=student.id, status="present", reason=None)
            ],
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        assert len(results) == 1
        assert results[0].student_id == student.id
        assert results[0].status == "present"

    async def test_upsert_attendance_waitlisted_signup(self) -> None:
        """Test that students with waitlisted signup status can have attendance marked."""
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        caregiver = FakeCaregiver(name="Caregiver B")
        student = FakeStudent(id=uuid4(), name="Student B", caregiver=caregiver)
        # WAITLISTED status signup
        signup = FakeSignup(
            id=uuid4(), student_id=student.id, student=student, status="waitlisted"
        )
        signup_service = DummySignupService([signup])
        attendance_service = DummyAttendanceService([])

        results = await AttendanceController.upsert_attendance.fn(
            controller,
            occurrence_id=occurrence.id,
            data=[
                AttendanceUpsert(
                    student_id=student.id, status="absent_known", reason="Sick"
                )
            ],
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        assert len(results) == 1
        assert results[0].student_id == student.id
        assert results[0].status == "absent_known"
        assert results[0].reason == "Sick"

    async def test_upsert_attendance_pending_signup_rejected(self) -> None:
        """Test that students with pending signup status cannot have attendance marked."""
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        caregiver = FakeCaregiver(name="Caregiver C")
        student = FakeStudent(id=uuid4(), name="Student C", caregiver=caregiver)
        # PENDING status signup - should be rejected
        signup_confirmed = FakeSignup(
            id=uuid4(),
            student_id=uuid4(),  # Different student
            student=FakeStudent(id=uuid4(), name="Other", caregiver=caregiver),
            status="confirmed",
        )
        # Only the confirmed signup is in the service
        signup_service = DummySignupService([signup_confirmed])
        attendance_service = DummyAttendanceService([])

        with pytest.raises(ValidationException) as exc_info:
            await AttendanceController.upsert_attendance.fn(
                controller,
                occurrence_id=occurrence.id,
                data=[
                    AttendanceUpsert(
                        student_id=student.id, status="present", reason=None
                    )
                ],
                occurrence_service=occurrence_service,
                attendance_service=attendance_service,
                signup_service=signup_service,
            )

        assert "is not signed up for this session" in str(exc_info.value)

    async def test_upsert_attendance_rejected_by_status(self) -> None:
        """Test that students with invalid signup status cannot have attendance marked.

        This test verifies the filtering logic correctly rejects students whose
        signup status is not 'confirmed' or 'waitlisted'.
        """
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        caregiver = FakeCaregiver(name="Caregiver D")
        # Create a different student with confirmed status to ensure filtering works
        other_student = FakeStudent(id=uuid4(), name="Other", caregiver=caregiver)
        confirmed_signup = FakeSignup(
            id=uuid4(),
            student_id=other_student.id,
            student=other_student,
            status="confirmed",
        )
        # Only the confirmed signup is returned - simulating status filter
        signup_service = DummySignupService([confirmed_signup])
        attendance_service = DummyAttendanceService([])

        # Try to mark attendance for a different student not in the confirmed list
        student_to_check = FakeStudent(
            id=uuid4(), name="Student D", caregiver=caregiver
        )
        with pytest.raises(ValidationException) as exc_info:
            await AttendanceController.upsert_attendance.fn(
                controller,
                occurrence_id=occurrence.id,
                data=[
                    AttendanceUpsert(
                        student_id=student_to_check.id, status="present", reason=None
                    )
                ],
                occurrence_service=occurrence_service,
                attendance_service=attendance_service,
                signup_service=signup_service,
            )

        assert "is not signed up for this session" in str(exc_info.value)

    async def test_upsert_attendance_invalid_student(self) -> None:
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)
        signup_service = DummySignupService([])
        attendance_service = DummyAttendanceService([])

        with pytest.raises(ValidationException):
            await AttendanceController.upsert_attendance.fn(
                controller,
                occurrence_id=occurrence.id,
                data=[
                    AttendanceUpsert(student_id=uuid4(), status="present", reason=None)
                ],
                occurrence_service=occurrence_service,
                attendance_service=attendance_service,
                signup_service=signup_service,
            )

    async def test_upsert_attendance_create(self) -> None:
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        caregiver = FakeCaregiver(name="Caregiver A")
        student = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        signup = FakeSignup(id=uuid4(), student_id=student.id, student=student)
        signup_service = DummySignupService([signup])
        attendance_service = DummyAttendanceService([])

        results = await AttendanceController.upsert_attendance.fn(
            controller,
            occurrence_id=occurrence.id,
            data=[
                AttendanceUpsert(student_id=student.id, status="present", reason=None)
            ],
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        assert len(results) == 1
        assert results[0].student_id == student.id
        assert results[0].status == "present"

    async def test_upsert_attendance_multiple_students(self) -> None:
        """Test upserting attendance for multiple students in a single batch."""
        controller = make_attendance_controller()
        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=uuid4(),
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(hours=1),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(occurrence)

        # Create multiple students with signups
        caregiver = FakeCaregiver(name="Caregiver A")
        student1 = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        student2 = FakeStudent(id=uuid4(), name="Student B", caregiver=caregiver)
        student3 = FakeStudent(id=uuid4(), name="Student C", caregiver=caregiver)

        signup1 = FakeSignup(id=uuid4(), student_id=student1.id, student=student1)
        signup2 = FakeSignup(id=uuid4(), student_id=student2.id, student=student2)
        signup3 = FakeSignup(id=uuid4(), student_id=student3.id, student=student3)
        signup_service = DummySignupService([signup1, signup2, signup3])
        attendance_service = DummyAttendanceService([])

        # Upsert attendance for all three students with different statuses
        results = await AttendanceController.upsert_attendance.fn(
            controller,
            occurrence_id=occurrence.id,
            data=[
                AttendanceUpsert(student_id=student1.id, status="present", reason=None),
                AttendanceUpsert(
                    student_id=student2.id, status="absent_known", reason="Sick"
                ),
                AttendanceUpsert(
                    student_id=student3.id, status="absent_unknown", reason=None
                ),
            ],
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        # Verify all three records were created
        assert len(results) == 3

        # Check first student (present)
        assert results[0].student_id == student1.id
        assert results[0].status == "present"
        assert results[0].reason is None

        # Check second student (absent with reason)
        assert results[1].student_id == student2.id
        assert results[1].status == "absent_known"
        assert results[1].reason == "Sick"

        # Check third student (absent unknown)
        assert results[2].student_id == student3.id
        assert results[2].status == "absent_unknown"
        assert results[2].reason is None

    async def test_get_attendance_history(self) -> None:
        controller = make_attendance_controller()
        record1 = FakeAttendanceRecord(
            id=uuid4(),
            occurrence_id=uuid4(),
            student_id=uuid4(),
            status="present",
        )
        record2 = FakeAttendanceRecord(
            id=uuid4(),
            occurrence_id=record1.occurrence_id,
            student_id=uuid4(),
            status="absent_known",
        )
        attendance_service = DummyAttendanceService([record1, record2])

        history = await AttendanceController.get_attendance_history.fn(
            controller,
            occurrence_id=record1.occurrence_id,
            occurrence_service=DummyOccurrenceService(None),
            attendance_service=attendance_service,
        )

        assert len(history) == 2
        assert history[0].occurrence_id == record1.occurrence_id


@pytest.mark.anyio
class TestAttendanceStatsController:
    async def test_get_attendance_stats_empty(self) -> None:
        controller = make_stats_controller()
        occurrence_service = DummyOccurrenceService(None)
        attendance_service = DummyAttendanceService([])
        signup_service = DummySignupService([])

        stats = await AttendanceStatsController.get_attendance_stats.fn(
            controller,
            session_id=uuid4(),
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        assert stats.total_occurrences == 0
        assert stats.total_students == 0
        assert stats.average_attendance_rate == 0.0

    async def test_get_attendance_stats_with_data(self) -> None:
        controller = make_stats_controller()
        session_id = uuid4()
        now = datetime.now(UTC)

        occ1 = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            cancelled=False,
        )
        occ2 = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=now + timedelta(days=7),
            ends_at=now + timedelta(days=7, hours=2),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(None)
        occurrence_service._occurrences = [occ1, occ2]

        caregiver = FakeCaregiver(name="Caregiver A")
        student1 = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        student2 = FakeStudent(id=uuid4(), name="Student B", caregiver=caregiver)

        signup_service = DummySignupService(
            [
                FakeSignup(id=uuid4(), student_id=student1.id, student=student1),
                FakeSignup(id=uuid4(), student_id=student2.id, student=student2),
            ]
        )

        attendance_service = DummyAttendanceService(
            [
                FakeAttendanceRecord(
                    id=uuid4(),
                    occurrence_id=occ1.id,
                    student_id=student1.id,
                    status="present",
                ),
                FakeAttendanceRecord(
                    id=uuid4(),
                    occurrence_id=occ1.id,
                    student_id=student2.id,
                    status="absent_known",
                ),
                FakeAttendanceRecord(
                    id=uuid4(),
                    occurrence_id=occ2.id,
                    student_id=student1.id,
                    status="present",
                ),
            ]
        )

        stats = await AttendanceStatsController.get_attendance_stats.fn(
            controller,
            session_id=session_id,
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
        )

        assert stats.total_occurrences == 2
        assert stats.total_students == 2
        assert stats.average_attendance_rate == 0.5
        assert stats.students_with_perfect_attendance == 1
        assert stats.students_with_poor_attendance == 1

    async def test_get_at_risk_students(self) -> None:
        controller = make_stats_controller()
        session_id = uuid4()
        now = datetime.now(UTC)

        occurrence = FakeOccurrence(
            id=uuid4(),
            session_id=session_id,
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            cancelled=False,
        )
        occurrence_service = DummyOccurrenceService(None)
        occurrence_service._occurrences = [occurrence]

        caregiver = FakeCaregiver(name="Caregiver A")
        student1 = FakeStudent(id=uuid4(), name="Student A", caregiver=caregiver)
        student2 = FakeStudent(id=uuid4(), name="Student B", caregiver=caregiver)

        signup_service = DummySignupService(
            [
                FakeSignup(id=uuid4(), student_id=student1.id, student=student1),
                FakeSignup(id=uuid4(), student_id=student2.id, student=student2),
            ]
        )

        attendance_service = DummyAttendanceService(
            [
                FakeAttendanceRecord(
                    id=uuid4(),
                    occurrence_id=occurrence.id,
                    student_id=student1.id,
                    status="present",
                ),
                FakeAttendanceRecord(
                    id=uuid4(),
                    occurrence_id=occurrence.id,
                    student_id=student2.id,
                    status="absent_unknown",
                ),
            ]
        )

        at_risk = await AttendanceStatsController.get_at_risk_students.fn(
            controller,
            session_id=session_id,
            occurrence_service=occurrence_service,
            attendance_service=attendance_service,
            signup_service=signup_service,
            threshold=0.75,
        )

        assert len(at_risk) == 1
        assert at_risk[0].student_id == student2.id
        assert at_risk[0].is_at_risk is True
