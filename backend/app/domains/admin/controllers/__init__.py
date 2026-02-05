from app.domains.admin.controllers.attendance import (
    AttendanceController as AdminAttendanceController,
)
from app.domains.admin.controllers.attendance import (
    AttendanceStatsController as AdminAttendanceStatsController,
)
from app.domains.admin.controllers.auth import AdminAuthController
from app.domains.admin.controllers.blocks import BlockController as AdminBlockController
from app.domains.admin.controllers.caregiver import (
    CaregiverController as AdminCaregiverController,
)
from app.domains.admin.controllers.exclusions import (
    ExclusionController as AdminExclusionController,
)
from app.domains.admin.controllers.locations import (
    LocationController as AdminLocationController,
)
from app.domains.admin.controllers.occurrences import (
    OccurrenceController as AdminOccurrenceController,
)
from app.domains.admin.controllers.sessions import (
    SessionController as AdminSessionController,
)
from app.domains.admin.controllers.signups import (
    SignupController as AdminSignupController,
)
from app.domains.admin.controllers.staff import SessionStaffController, StaffController
from app.domains.admin.controllers.students import (
    StudentController as AdminStudentController,
)

__all__ = [
    "AdminAttendanceController",
    "AdminAttendanceStatsController",
    "AdminAuthController",
    "AdminBlockController",
    "AdminCaregiverController",
    "AdminExclusionController",
    "AdminLocationController",
    "AdminOccurrenceController",
    "AdminSessionController",
    "AdminSignupController",
    "SessionStaffController",
    "StaffController",
    "AdminStudentController",
]
