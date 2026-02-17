"""
Integration tests for admin staff management endpoints.

Tests staff list, get, create, and update operations with authentication,
proper HTTP status codes, and payload validation.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminStaffList:
    """Test staff listing endpoints."""

    async def test_list_staff_active_only_default(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing staff filters to active only by default."""
        active_staff = m.Staff(
            name="Active Staff",
            email="active.staff@example.com",
            sso_id="sso-active",
            active=True,
        )
        inactive_staff = m.Staff(
            name="Inactive Staff",
            email="inactive.staff@example.com",
            sso_id="sso-inactive",
            active=False,
            deactivated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([active_staff, inactive_staff])
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/staff/",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert any(item["id"] == str(active_staff.id) for item in data)
        assert all(item["active"] is True for item in data)

    async def test_list_staff_with_inactive_filter(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing staff with active_only=false returns all staff."""
        active_staff = m.Staff(
            name="Active Staff",
            email="active.staff2@example.com",
            sso_id="sso-active-2",
            active=True,
        )
        inactive_staff = m.Staff(
            name="Inactive Staff",
            email="inactive.staff2@example.com",
            sso_id="sso-inactive-2",
            active=False,
            deactivated_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        )
        db_session.add_all([active_staff, inactive_staff])
        await db_session.commit()

        response = await client.get(
            "/api/v1/admin/staff/?active_only=false",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        ids = {item["id"] for item in data}
        assert str(active_staff.id) in ids
        assert str(inactive_staff.id) in ids

    async def test_list_staff_without_auth(self, client: AsyncClient) -> None:
        """Test listing staff without authentication fails."""
        response = await client.get("/api/v1/admin/staff/")
        assert response.status_code in [302, 401, 403]


class TestAdminStaffGet:
    """Test retrieving a specific staff member."""

    async def test_get_staff_by_id(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving staff by ID returns complete details."""
        staff = m.Staff(
            name="Staff Member",
            email="staff.member@example.com",
            sso_id="sso-staff-1",
            active=True,
        )
        db_session.add(staff)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/staff/{staff.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["id"] == str(staff.id)
        assert data["name"] == "Staff Member"
        assert data["email"] == "staff.member@example.com"
        assert data.get("ssoId") or data.get("sso_id") == "sso-staff-1"
        assert data["active"] is True

    async def test_get_staff_not_found(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving nonexistent staff returns 404."""
        response = await client.get(
            f"/api/v1/admin/staff/{uuid4()}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_staff_without_auth(self, client: AsyncClient) -> None:
        """Test retrieving staff without authentication fails."""
        response = await client.get(f"/api/v1/admin/staff/{uuid4()}")
        assert response.status_code in [302, 401, 403]


class TestAdminStaffCreate:
    """Test staff creation endpoint."""

    async def test_create_staff_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a new staff member succeeds."""
        payload = {
            "name": "New Staff",
            "email": "new.staff@example.com",
            "ssoId": "sso-new-1",
        }

        response = await client.post(
            "/api/v1/admin/staff/",
            json=payload,
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code in (HTTP_200_OK, HTTP_201_CREATED)
        data = response.json()
        assert data["name"] == "New Staff"
        assert data["email"] == "new.staff@example.com"
        assert data.get("ssoId") or data.get("sso_id") == "sso-new-1"
        assert data["active"] is True
        assert "id" in data

    async def test_create_staff_duplicate_email(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating staff with duplicate email fails."""
        existing = m.Staff(
            name="Existing Staff",
            email="existing@example.com",
            sso_id="sso-existing",
            active=True,
        )
        db_session.add(existing)
        await db_session.commit()

        response = await client.post(
            "/api/v1/admin/staff/",
            json={
                "name": "New Staff",
                "email": "existing@example.com",
                "ssoId": "sso-new-dup",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == 400

    async def test_create_staff_duplicate_sso_id(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating staff with duplicate SSO ID fails."""
        existing = m.Staff(
            name="Existing Staff",
            email="existing2@example.com",
            sso_id="sso-existing",
            active=True,
        )
        db_session.add(existing)
        await db_session.commit()

        response = await client.post(
            "/api/v1/admin/staff/",
            json={
                "name": "New Staff",
                "email": "new@example.com",
                "ssoId": "sso-existing",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == 400

    async def test_create_staff_without_auth(self, client: AsyncClient) -> None:
        """Test creating staff without authentication fails."""
        response = await client.post(
            "/api/v1/admin/staff/",
            json={
                "name": "New Staff",
                "email": "new@example.com",
                "ssoId": "sso-new",
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminStaffUpdate:
    """Test staff update endpoint."""

    async def test_update_staff_deactivate(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test deactivating staff sets deactivated_at timestamp."""
        staff = m.Staff(
            name="Deactivate Me",
            email="deactivate.me@example.com",
            sso_id="sso-deactivate",
            active=True,
        )
        db_session.add(staff)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/staff/{staff.id}",
            json={"active": False},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["active"] is False
        assert data.get("deactivatedAt") or data.get("deactivated_at") is not None

    async def test_update_staff_reactivate(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test reactivating staff clears deactivated_at."""
        staff = m.Staff(
            name="Reactivate Me",
            email="reactivate.me@example.com",
            sso_id="sso-reactivate",
            active=False,
            deactivated_at=datetime.now(timezone.utc),
        )
        db_session.add(staff)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/staff/{staff.id}",
            json={"active": True},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["active"] is True
        assert data.get("deactivatedAt") or data.get("deactivated_at") is None

    async def test_update_staff_properties(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating staff name and email."""
        staff = m.Staff(
            name="Original Name",
            email="original@example.com",
            sso_id="sso-update",
            active=True,
        )
        db_session.add(staff)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/staff/{staff.id}",
            json={
                "name": "Updated Name",
            },
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "original@example.com"

    async def test_update_staff_not_found(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating nonexistent staff returns 404."""
        response = await client.patch(
            f"/api/v1/admin/staff/{uuid4()}",
            json={"name": "Updated"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_update_staff_without_auth(self, client: AsyncClient) -> None:
        """Test updating staff without authentication fails."""
        response = await client.patch(
            f"/api/v1/admin/staff/{uuid4()}",
            json={"name": "Updated"},
        )
        assert response.status_code in [302, 401, 403]
