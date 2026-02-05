"""Production-ready field validation utilities with comprehensive security checks."""

import re
import unicodedata
from typing import Annotated, Any

import msgspec

from app.lib.exceptions import ApplicationClientError

EMAIL_BASIC_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]\.[a-zA-Z]{2,}$"
)
EMAIL_DOUBLE_DOT_PATTERN = re.compile(r"\.\.+")
EMAIL_BLOCKED_PATTERNS = [
    re.compile(r".*\+.*test.*@.*"),
    re.compile(r".*\+.*spam.*@.*"),
    re.compile(r"^test.*@.*"),
    re.compile(r"^noreply@.*"),
    re.compile(r"^no-reply@.*"),
]

NAME_WHITESPACE_PATTERN = re.compile(r"\s+")
NAME_VALID_PATTERN = re.compile(
    r"^[a-zA-ZÀ-ÿĀ-žА-я\u4e00-\u9fff\u0600-\u06ff\u3040-\u309f\u30a0-\u30ff\s'\-\.]+$"
)
NAME_REPEATED_PATTERN = re.compile(r"(.)\1{4,}")

PHONE_BASIC_PATTERN = re.compile(r"^[\+]?[0-9\s\-\(\)\.]+$")
PHONE_DIGITS_PATTERN = re.compile(r"[^\d]")

PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15

EMAIL_MAX_LENGTH = 254
EMAIL_MIN_LENGTH = 3
EMAIL_LOCAL_PART_MAX_LENGTH = 64

NAME_MAX_LENGTH = 100


class ValidationError(ApplicationClientError):
    """Custom validation error for all field validations.

    Inherits from ApplicationClientError for proper exception hierarchy integration.
    The exception_to_http_response handler converts this to HTTP 400 Bad Request.
    """


def _ensure_str(
    value: Any, field_name: str, exc_type: type[ValidationError] = ValidationError
) -> str:
    """Ensure the value is a string.

    Args:
        value: The value to validate.
        field_name: Field label used in error messages.
        exc_type: Exception type to raise on validation failure.

    Returns:
        The validated string.
    """
    if not isinstance(value, str):
        msg = f"{field_name} must be a string"
        raise exc_type(msg)
    return value


def validate_not_empty(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        msg = "Value cannot be empty"
        raise ValidationError(msg)
    return cleaned


def validate_length(
    value: str, min_length: int = 0, max_length: int | None = None
) -> str:
    if len(value) < min_length:
        msg = f"Must be at least {min_length} characters"
        raise ValidationError(msg)
    if max_length and len(value) > max_length:
        msg = f"Must not exceed {max_length} characters"
        raise ValidationError(msg)
    return value


def validate_no_control_chars(value: str) -> str:
    """Remove/reject control characters.

    Args:
        value: The string to validate.

    Raises:
        ValidationError: If control characters are found.

    Returns:
        The cleansed string without control characters.
    """
    if any(
        unicodedata.category(char) == "Cc" for char in value if char not in "\n\r\t"
    ):
        msg = "Contains invalid control characters"
        raise ValidationError(msg)
    return value


def validate_email(v: str) -> str:
    """Production-ready email validation with comprehensive checks.

    Args:
        v: The email address to validate.

    Returns:
        The normalized email address.

    Raises:
        ValidationError: If validation fails.
    """
    v = _ensure_str(v, "Email")

    email = v.strip().lower()

    if len(email) > EMAIL_MAX_LENGTH:
        msg = "Email address too long"
        raise ValidationError(msg)

    if len(email) < EMAIL_MIN_LENGTH:
        msg = "Email address too short"
        raise ValidationError(msg)

    if not EMAIL_BASIC_PATTERN.match(email):
        msg = "Invalid email format"
        raise ValidationError(msg)

    if EMAIL_DOUBLE_DOT_PATTERN.search(email):
        msg = "Invalid email format"
        raise ValidationError(msg)

    local_part, _, _ = email.rpartition("@")

    for pattern in EMAIL_BLOCKED_PATTERNS:
        if pattern.match(email):
            msg = "Email format not allowed"
            raise ValidationError(msg)

    if len(local_part) > EMAIL_LOCAL_PART_MAX_LENGTH:
        msg = "Email local part too long"
        raise ValidationError(msg)

    return email


Email = Annotated[str, msgspec.Meta(description="Valid email address")]


def validate_name(v: str) -> str:
    """Human name validation with proper handling of international names.

    Args:
        v: The name to validate.

    Returns:
        The normalized name.

    Raises:
        ValidationError: If validation fails.
    """
    v = _ensure_str(v, "Name")

    name = v.strip()
    name = NAME_WHITESPACE_PATTERN.sub(" ", name)

    if len(name) < 1:
        msg = "Name cannot be empty"
        raise ValidationError(msg)
    if len(name) > NAME_MAX_LENGTH:
        msg = f"Name must not exceed {NAME_MAX_LENGTH} characters"
        raise ValidationError(msg)

    if not NAME_VALID_PATTERN.match(name):
        msg = "Name contains invalid characters"
        raise ValidationError(msg)

    if NAME_REPEATED_PATTERN.search(name):
        msg = "Name contains suspicious patterns"
        raise ValidationError(msg)

    return name


Name = Annotated[str, msgspec.Meta(description="Human name (1-100 characters)")]


def validate_phone(v: str) -> str:
    """International phone number validation.

    Args:
        v: The phone number to validate.

    Returns:
        The normalized phone number.

    Raises:
        ValidationError: If validation fails.
    """
    v = _ensure_str(v, "Phone number")

    phone = v.strip()

    if not phone:
        msg = "Phone number cannot be empty"
        raise ValidationError(msg)

    if not PHONE_BASIC_PATTERN.match(phone):
        msg = "Invalid phone number format"
        raise ValidationError(msg)

    digits_only = PHONE_DIGITS_PATTERN.sub("", phone)
    if len(digits_only) < PHONE_MIN_DIGITS or len(digits_only) > PHONE_MAX_DIGITS:
        msg = f"Phone number must be between {PHONE_MIN_DIGITS} and {PHONE_MAX_DIGITS} digits"
        raise ValidationError(msg)

    return phone


Phone = Annotated[str, msgspec.Meta(description="Valid international phone number")]


def validate_time_range(start_time: Any, end_time: Any) -> None:
    """Validate that end_time is after start_time.

    Args:
        start_time: Session start time
        end_time: Session end time

    Raises:
        ValidationError: If end_time is not after start_time
    """
    if end_time <= start_time:
        msg = "Session end time must be after start time"
        raise ValidationError(msg)


def validate_age_range(age_lower: int, age_upper: int) -> None:
    """Validate that age range is valid.

    Args:
        age_lower: Minimum age
        age_upper: Maximum age

    Raises:
        ValidationError: If range is invalid
    """
    if age_lower < 0:
        msg = "Minimum age cannot be negative"
        raise ValidationError(msg)

    if age_upper < age_lower:
        msg = "Maximum age must be greater than or equal to minimum age"
        raise ValidationError(msg)

    if age_upper > 100:
        msg = "Maximum age cannot exceed 100"
        raise ValidationError(msg)


def validate_capacity(capacity: int) -> None:
    """Validate session capacity.

    Args:
        capacity: Maximum number of participants

    Raises:
        ValidationError: If capacity is invalid
    """
    if capacity <= 0:
        msg = "Capacity must be greater than 0"
        raise ValidationError(msg)

    if capacity > 500:
        msg = "Capacity cannot exceed 500"
        raise ValidationError(msg)
