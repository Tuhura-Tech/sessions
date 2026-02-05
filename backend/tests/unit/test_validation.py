from __future__ import annotations

from datetime import time

import pytest

from app.lib.validation import (
    ValidationError,
    validate_age_range,
    validate_capacity,
    validate_email,
    validate_name,
    validate_no_control_chars,
    validate_phone,
    validate_time_range,
)


def test_validate_email_accepts_valid() -> None:
    assert validate_email("user@example.com") == "user@example.com"


def test_validate_email_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_email("not-an-email")


def test_validate_name_accepts_unicode() -> None:
    assert validate_name("Jean-Luc Picard") == "Jean-Luc Picard"


def test_validate_name_rejects_invalid_chars() -> None:
    with pytest.raises(ValidationError):
        validate_name("Bad$$Name")


def test_validate_phone_accepts_valid() -> None:
    assert validate_phone("+1 234 567 8901") == "+1 234 567 8901"


def test_validate_phone_rejects_invalid() -> None:
    with pytest.raises(ValidationError):
        validate_phone("abc123")


def test_validate_no_control_chars() -> None:
    assert validate_no_control_chars("Hello\nWorld") == "Hello\nWorld"
    with pytest.raises(ValidationError):
        validate_no_control_chars("Bad\x00Name")


def test_validate_time_range() -> None:
    validate_time_range(time(9, 0), time(10, 0))
    with pytest.raises(ValidationError):
        validate_time_range(time(10, 0), time(9, 0))


def test_validate_age_range() -> None:
    validate_age_range(5, 12)
    with pytest.raises(ValidationError):
        validate_age_range(-1, 10)
    with pytest.raises(ValidationError):
        validate_age_range(12, 10)
    with pytest.raises(ValidationError):
        validate_age_range(5, 101)


def test_validate_capacity() -> None:
    validate_capacity(10)
    with pytest.raises(ValidationError):
        validate_capacity(0)
    with pytest.raises(ValidationError):
        validate_capacity(501)
