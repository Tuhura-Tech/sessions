"""Age calculation utilities."""

from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta


def calculate_age(birth_date: date) -> int:
    """Calculate accurate age from birth date.

    Accounts for leap years and exact birthdays.

    Args:
        birth_date: The person's date of birth

    Returns:
        Age in complete years

    Example:
        >>> calculate_age(date(2020, 1, 15))
        6  # If today is after Jan 15, 2026
    """
    today = date.today()
    age_delta = relativedelta(today, birth_date)
    return age_delta.years


def is_age_eligible(
    birth_date: date | None,
    age_lower: int | None,
    age_upper: int | None,
) -> tuple[bool, str | None]:
    """Check if age is within acceptable range for a session.

    Args:
        birth_date: Person's date of birth (None if unknown)
        age_lower: Minimum age (inclusive), or None for no limit
        age_upper: Maximum age (inclusive), or None for no limit

    Returns:
        Tuple of (is_eligible, reason_if_ineligible)
        If eligible, reason is None.
    """
    if not birth_date:
        # No DOB - can't determine eligibility
        return False, "Date of birth required for age verification"

    age = calculate_age(birth_date)

    if age_lower is not None and age < age_lower:
        return False, f"Too young (must be at least {age_lower} years old)"

    if age_upper is not None and age > age_upper:
        return False, f"Too old (must be {age_upper} years old or younger)"

    return True, None
