from app.domains.caregiver.controllers.auth import CaregiverAuthController
from app.domains.caregiver.controllers.caregiver import CaregiverController
from app.domains.caregiver.controllers.signup import (
    SignupController as CaregiverSignupController,
)
from app.domains.caregiver.controllers.student import (
    StudentController as CaregiverStudentController,
)

__all__ = [
    "CaregiverController",
    "CaregiverAuthController",
    "CaregiverSignupController",
    "CaregiverStudentController",
]
