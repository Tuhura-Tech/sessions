from __future__ import annotations

from app.db import models as m

_DAY_NAMES = (
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
)


def format_session_time(session: m.Session) -> str | None:
    """Return a display string like 'Monday 09:00-10:00' or None.

    Special sessions may not have a day_of_week, so return None in that case.
    """
    if session.day_of_week is None:
        return None

    day_name = _DAY_NAMES[int(session.day_of_week)]
    return (
        f"{day_name} {session.start_time.strftime('%H:%M')}"
        f"-{session.end_time.strftime('%H:%M')}"
    )
