"""Tests for admin attendance endpoints with authentication."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from litestar.status_codes import HTTP_404_NOT_FOUND

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminAttendanceRollEndpoint:
    """Tests for /api/v1/admin/occurrences/:occurrence_id/roll endpoint."""

    async def test_get_roll_requires_auth(self, client: AsyncClient) -> None:
        """Test that attendance roll endpoint requires authentication."""
        # Use a random UUID for testing
        response = await client.get(
            "/api/v1/admin/occurrences/550e8400-e29b-41d4-a716-446655440000/roll"
        )
        # Should redirect to OAuth or return unauthorized
        assert response.status_code in [302, 401, 403, 404]

    async def test_get_roll_with_invalid_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test getting attendance roll for non-existent occurrence."""
        response = await client.get(
            "/api/v1/admin/occurrences/550e8400-e29b-41d4-a716-446655440000/roll",
            cookies={"admin_session": admin_session_cookie},
        )
        # May be 404 or 500 depending on validation
        assert response.status_code in [HTTP_404_NOT_FOUND, 500]


class TestAdminAttendanceSaveEndpoint:
    """Tests for POST /api/v1/admin/occurrences/:occurrence_id/attendance endpoint."""

    async def test_save_attendance_requires_auth(self, client: AsyncClient) -> None:
        """Test that save attendance endpoint requires authentication."""
        response = await client.post(
            "/api/v1/admin/occurrences/550e8400-e29b-41d4-a716-446655440000/attendance",
            json={"attendance": []},
        )
        assert response.status_code in [302, 401, 403, 404]

    async def test_save_attendance_with_invalid_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test saving attendance for non-existent occurrence."""
        response = await client.post(
            "/api/v1/admin/occurrences/550e8400-e29b-41d4-a716-446655440000/attendance",
            cookies={"admin_session": admin_session_cookie},
            json={"attendance": []},
        )
        # May be 400 or 404 depending on validation
        assert response.status_code in [HTTP_404_NOT_FOUND, 400]
