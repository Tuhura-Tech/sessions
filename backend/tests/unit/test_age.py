from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from app.lib.age import calculate_age, is_age_eligible


def test_calculate_age_exact_years() -> None:
    birth_date = date.today() - relativedelta(years=10)
    assert calculate_age(birth_date) == 10


def test_is_age_eligible_requires_birth_date() -> None:
    eligible, reason = is_age_eligible(None, 5, 12)
    assert eligible is False
    assert reason is not None


def test_is_age_eligible_lower_and_upper_bounds() -> None:
    birth_date = date.today() - relativedelta(years=9)
    eligible, reason = is_age_eligible(birth_date, 8, 12)
    assert eligible is True
    assert reason is None

    too_young, reason = is_age_eligible(birth_date, 10, 12)
    assert too_young is False
    assert "Too young" in (reason or "")

    older_birth = date.today() - relativedelta(years=14)
    too_old, reason = is_age_eligible(older_birth, 8, 12)
    assert too_old is False
    assert "Too old" in (reason or "")
