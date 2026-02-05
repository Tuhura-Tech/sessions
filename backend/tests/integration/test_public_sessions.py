"""
Integration tests for public session endpoints.

Tests for public session listing and details endpoints accessible without authentication.
"""

from uuid import uuid4

import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session as SessionModel
from tests.integration.test_fixtures import create_test_location, create_test_session

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestPublicSessionListEndpoint:
    """Test public session listing endpoint."""

    async def test_list_sessions_empty(self, test_client):
        """Test GET /api/v1/sessions returns empty list when no sessions."""
        response = await test_client.get("/api/v1/sessions/")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) == 0
        assert "total" in data
        assert data["total"] == 0

    async def test_list_sessions_with_blocks_and_occurrences(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test GET /api/v1/sessions returns block names (not occurrences)."""
        location = await create_test_location(db_session)
        session = await create_test_session(
            db_session, location=location, name="Session 1"
        )

        # Add a block and occurrence
        from app.db.models import Block, Occurrence, BlockLink
        from datetime import datetime

        block = Block(
            name="Term 1",
            block_type="term_1",
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 4, 2),
            year=2026,
        )
        db_session.add(block)
        await db_session.flush()

        block_link = BlockLink(session_id=session.id, block_id=block.id)
        db_session.add(block_link)
        await db_session.flush()

        occ = Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 2, 11, 15, 30),
            ends_at=datetime(2026, 2, 11, 17, 30),
            cancelled=False,
        )
        db_session.add(occ)
        await db_session.commit()

        response = await test_client.get("/api/v1/sessions/")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        session_data = data["items"][0]
        assert "blocks" in session_data
        assert isinstance(session_data["blocks"], list)
        assert "Term 1" in session_data["blocks"]
        # Verify location data including coordinates
        assert "location" in session_data
        location_data = session_data["location"]
        assert "name" in location_data
        assert "address" in location_data
        assert "region" in location_data
        assert "lat" in location_data
        assert "lng" in location_data
        # Verify coordinates are in New Zealand range (not at 0,0)
        assert -47.5 < location_data["lat"] < -34.0, (
            f"Latitude {location_data['lat']} not in New Zealand range"
        )
        assert 166.0 < location_data["lng"] < 178.5, (
            f"Longitude {location_data['lng']} not in New Zealand range"
        )

    async def test_list_sessions_excludes_archived(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that archived sessions are excluded from list."""
        location = await create_test_location(db_session)

        # Create active session
        await create_test_session(db_session, location=location, name="Active")

        # Create archived session
        archived_session = SessionModel(
            name="Archived",
            location_id=location.id,
            year=2026,
            age_lower=5,
            age_upper=12,
            session_type="special",
            start_time=__import__("datetime").time(9, 0),
            end_time=__import__("datetime").time(17, 0),
            capacity=20,
            archived=True,
        )
        db_session.add(archived_session)
        await db_session.flush()

        # Test endpoint
        response = await test_client.get("/api/v1/sessions/")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Active"

    async def test_list_sessions_pagination(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test GET /api/v1/sessions supports pagination."""
        location = await create_test_location(db_session)

        # Create multiple sessions
        for i in range(5):
            await create_test_session(
                db_session, location=location, name=f"Session {i}"
            )

        # Test with limit
        response = await test_client.get("/api/v1/sessions/?limit=2")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    async def test_list_sessions_offset(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test GET /api/v1/sessions supports offset pagination."""
        location = await create_test_location(db_session)

        # Create multiple sessions
        for i in range(3):
            await create_test_session(
                db_session, location=location, name=f"Session {i}"
            )

        # Get first page
        response1 = await test_client.get("/api/v1/sessions/?limit=1&offset=0")
        assert response1.status_code == HTTP_200_OK

        # Get second page
        response2 = await test_client.get("/api/v1/sessions/?limit=1&offset=1")
        assert response2.status_code == HTTP_200_OK

        data1 = response1.json()
        data2 = response2.json()

        # Should be different sessions
        assert data1["items"][0]["id"] != data2["items"][0]["id"]

    async def test_list_sessions_negative_limit(self, test_client):
        response = await test_client.get("/api/v1/sessions/?limit=-1")
        assert response.status_code == HTTP_400_BAD_REQUEST

    async def test_list_sessions_negative_offset(self, test_client):
        response = await test_client.get("/api/v1/sessions/?offset=-1")
        assert response.status_code == HTTP_400_BAD_REQUEST


@pytest.mark.integration
class TestPublicSessionDetailEndpoint:
    """Test public session detail endpoint."""

    async def test_get_session_includes_blocks_and_occurrences(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test GET /api/v1/sessions/{id} includes blocks and occurrences."""
        location = await create_test_location(db_session, name="Downtown")
        session = await create_test_session(
            db_session, location=location, name="Test Session"
        )
        from app.db.models import Block, Occurrence, BlockLink
        from datetime import datetime

        block = Block(
            name="Term 1",
            block_type="term_1",
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 4, 2),
            year=2026,
        )
        db_session.add(block)
        await db_session.flush()
        block_link = BlockLink(session_id=session.id, block_id=block.id)
        db_session.add(block_link)
        await db_session.flush()
        occ = Occurrence(
            session_id=session.id,
            block_id=block.id,
            starts_at=datetime(2026, 2, 11, 15, 30),
            ends_at=datetime(2026, 2, 11, 17, 30),
            cancelled=False,
        )
        db_session.add(occ)
        await db_session.commit()

        response = await test_client.get(f"/api/v1/sessions/{session.id}")
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Session"
        assert str(data["id"]) == str(session.id)
        assert "blocks" in data
        assert "Term 1" in data["blocks"]
        assert "occurrences_by_block" in data
        assert isinstance(data["occurrences_by_block"], list)
        block_occ = data["occurrences_by_block"][0]
        assert block_occ["block_name"] == "Term 1"
        assert isinstance(block_occ["occurrences"], list)
        occ_data = block_occ["occurrences"][0]
        assert "starts_at" in occ_data
        assert "ends_at" in occ_data
        assert "cancelled" in occ_data
        # Verify location coordinates
        assert "location" in data
        location_data = data["location"]
        assert location_data["name"] == "Downtown"
        assert "lat" in location_data
        assert "lng" in location_data
        # Verify coordinates are in New Zealand range
        assert -47.5 < location_data["lat"] < -34.0, (
            f"Latitude {location_data['lat']} not in New Zealand range"
        )
        assert 166.0 < location_data["lng"] < 178.5, (
            f"Longitude {location_data['lng']} not in New Zealand range"
        )

    async def test_get_session_not_found(self, test_client):
        """Test GET /api/v1/sessions/{id} returns 404 for non-existent session."""
        fake_id = uuid4()
        response = await test_client.get(f"/api/v1/sessions/{fake_id}")
        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_archived_session_not_found(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that archived sessions cannot be retrieved directly."""
        location = await create_test_location(db_session)

        # Create archived session
        archived = SessionModel(
            name="Archived",
            location_id=location.id,
            year=2026,
            age_lower=5,
            age_upper=12,
            session_type="special",
            start_time=__import__("datetime").time(9, 0),
            end_time=__import__("datetime").time(17, 0),
            capacity=20,
            archived=True,
        )
        db_session.add(archived)
        await db_session.flush()

        # Try to get it
        response = await test_client.get(f"/api/v1/sessions/{archived.id}")
        assert response.status_code == HTTP_404_NOT_FOUND

    async def test_get_session_includes_location(
        self,
        test_client,
        db_session: AsyncSession,
    ):
        """Test that session includes location details."""
        location = await create_test_location(
            db_session, name="Test Location", address="123 Main St"
        )
        session = await create_test_session(db_session, location=location)

        response = await test_client.get(f"/api/v1/sessions/{session.id}")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["location"]["name"] == "Test Location"
        assert data["location"]["address"] == "123 Main St"
