"""
Integration tests for admin occurrence management endpoints.

Tests occurrence get by ID, create, update, and cancel operations.
Note: No list endpoint exists for occurrences - only individual operations.
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
from tests.integration.test_fixtures import (
    create_test_location,
    create_test_session,
    create_test_block,
)

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminOccurrenceGet:
    """Test retrieving occurrence by ID."""

    async def test_get_occurrence_by_id(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving specific occurrence returns complete data."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 4, 10, 10, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 4, 10, 16, 0, tzinfo=timezone.utc),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.get(
            f"/api/v1/admin/occurrences/{occurrence.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["cancelled"] is False
        assert "startsAt" in data or "starts_at" in data
        assert "endsAt" in data or "ends_at" in data

    async def test_get_nonexistent_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent occurrence returns 404."""
        response = await client.get(
            f"/api/v1/admin/occurrences/{uuid4()}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_occurrence_without_auth(self, client: AsyncClient) -> None:
        """Test retrieving occurrence without authentication fails."""
        response = await client.get(f"/api/v1/admin/occurrences/{uuid4()}")
        assert response.status_code in [302, 401, 403]


class TestAdminOccurrenceCreate:
    """Test occurrence creation."""

    async def test_create_occurrence_success(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test creating a new occurrence succeeds."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence_data = {
            "sessionId": str(session.id),
            "blockId": str(block.id),
            "startsAt": "2026-05-15T09:00:00Z",
            "endsAt": "2026-05-15T15:00:00Z",
        }

        response = await client.post(
            "/api/v1/admin/occurrences/",
            json=occurrence_data,
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data.get("cancelled") is not None
        assert "id" in data

    async def test_create_occurrence_without_auth(self, client: AsyncClient) -> None:
        """Test creating occurrence without authentication fails."""
        response = await client.post(
            "/api/v1/admin/occurrences/",
            json={
                "sessionId": str(uuid4()),
                "blockId": str(uuid4()),
                "startsAt": "2026-05-15T09:00:00Z",
                "endsAt": "2026-05-15T15:00:00Z",
            },
        )
        assert response.status_code in [302, 401, 403]


class TestAdminOccurrenceUpdate:
    """Test occurrence update operations."""

    async def test_update_occurrence_times(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating occurrence start and end times."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc),
        )
        db_session.add(occurrence)
        await db_session.commit()

        update_data = {
            "startsAt": "2026-06-01T10:00:00Z",
            "endsAt": "2026-06-01T16:00:00Z",
        }

        response = await client.patch(
            f"/api/v1/admin/occurrences/{occurrence.id}",
            json=update_data,
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data.get("startsAt") or data.get("starts_at") == "2026-06-01T10:00:00Z"

        # Verify database was updated
        await db_session.refresh(occurrence)
        assert occurrence.starts_at == datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        assert occurrence.ends_at == datetime(2026, 6, 1, 16, 0, tzinfo=timezone.utc)

    async def test_cancel_occurrence(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test cancelling an occurrence."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 1, 15, 0, tzinfo=timezone.utc),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/occurrences/{occurrence.id}/cancel",
            json={"cancelled": True},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["cancelled"] is True

        # Verify database was updated
        await db_session.refresh(occurrence)
        assert occurrence.cancelled is True

    async def test_cancel_occurrence_with_reason(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test cancelling an occurrence with a reason."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 8, 1, 15, 0, tzinfo=timezone.utc),
            cancelled=False,
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/occurrences/{occurrence.id}/cancel",
            json={"cancelled": True, "cancellationReason": "Bad weather"},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["cancelled"] is True

        # Verify database was updated with reason
        await db_session.refresh(occurrence)
        assert occurrence.cancelled is True
        assert occurrence.cancellation_reason == "Bad weather"

    async def test_reinstate_cancelled_occurrence(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test reinstating a cancelled occurrence."""
        location = await create_test_location(db_session)
        session = await create_test_session(db_session, location=location)
        block = await create_test_block(db_session)

        occurrence = m.Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 9, 1, 15, 0, tzinfo=timezone.utc),
            cancelled=True,
            cancellation_reason="Bad weather",
        )
        db_session.add(occurrence)
        await db_session.commit()

        response = await client.patch(
            f"/api/v1/admin/occurrences/{occurrence.id}/cancel",
            json={"cancelled": False},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["cancelled"] is False

        # Verify database was updated
        await db_session.refresh(occurrence)
        assert occurrence.cancelled is False

    async def test_update_nonexistent_occurrence(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent occurrence returns 404."""
        response = await client.patch(
            f"/api/v1/admin/occurrences/{uuid4()}",
            json={"cancelled": True},
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_update_occurrence_without_auth(self, client: AsyncClient) -> None:
        """Test updating occurrence without authentication fails."""
        response = await client.patch(
            f"/api/v1/admin/occurrences/{uuid4()}",
            json={"cancelled": True},
        )
        assert response.status_code in [302, 401, 403]
