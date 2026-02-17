"""
Integration tests for admin block management endpoints.

Tests for block CRUD operations with proper authentication and data verification.
"""

import pytest
from httpx import AsyncClient
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_fixtures import create_test_block

pytestmark = [pytest.mark.anyio, pytest.mark.integration]


class TestAdminBlockList:
    """Test admin block listing endpoint."""

    async def test_list_blocks_empty(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test listing blocks when none exist."""
        response = await client.get(
            "/api/v1/admin/blocks/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        # Should have items list (even if empty)
        assert "items" in data or isinstance(data, list)

    async def test_list_blocks_with_data(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test listing blocks returns all created blocks."""
        # Create multiple blocks
        block1 = await create_test_block(
            db_session, year=2025, name="Block 1", block_type="holiday"
        )
        block2 = await create_test_block(
            db_session, year=2025, name="Block 2", block_type="holiday"
        )

        response = await client.get(
            "/api/v1/admin/blocks/",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_200_OK
        data = response.json()

        # Extract items - handle both dict with "items" and direct list
        items = data.get("items", data) if isinstance(data, dict) else data
        assert len(items) >= 2

        # Verify blocks are in list
        block_names = [item.get("name") for item in items]
        assert block1.name in block_names
        assert block2.name in block_names


class TestAdminBlockCreate:
    """Test admin block creation endpoint."""

    async def test_create_block_success(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test creating a new block with all required fields."""
        response = await client.post(
            "/api/v1/admin/blocks/",
            cookies={"admin_session": admin_session_cookie},
            json={
                "name": "Winter Break 2025",
                "block_type": "holiday",
                "start_date": "2025-12-20",
                "end_date": "2026-01-03",
                "year": 2025,
            },
        )

        assert response.status_code == HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Winter Break 2025"
        assert data["block_type"] == "holiday"
        assert data["year"] == 2025

    async def test_create_block_without_auth(self, client: AsyncClient) -> None:
        """Test creating a block without authentication fails."""
        response = await client.post(
            "/api/v1/admin/blocks/",
            json={
                "name": "Block",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
                "year": 2025,
            },
        )
        # Should redirect or return 401/403
        assert response.status_code in [302, 401, 403]


class TestAdminBlockGet:
    """Test retrieving a specific block."""

    async def test_get_block(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test retrieving a block by ID returns all fields."""
        block = await create_test_block(
            db_session, year=2025, name="Test Block", block_type="holiday"
        )

        response = await client.get(
            f"/api/v1/admin/blocks/{block.id}",
            cookies={"admin_session": admin_session_cookie},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Block"
        assert data["block_type"] == "holiday"
        assert str(data["id"]) == str(block.id)

    async def test_get_nonexistent_block(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test retrieving non-existent block returns 404."""
        response = await client.get(
            "/api/v1/admin/blocks/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
        )
        assert response.status_code == HTTP_404_NOT_FOUND


class TestAdminBlockUpdate:
    """Test updating a block."""

    async def test_update_block_name(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating block name succeeds."""
        block = await create_test_block(
            db_session, year=2025, name="Original", block_type="holiday"
        )

        response = await client.patch(
            f"/api/v1/admin/blocks/{block.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated Name"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["block_type"] == "holiday"  # Should remain unchanged

    async def test_update_block_type(
        self, client: AsyncClient, admin_session_cookie: str, db_session: AsyncSession
    ) -> None:
        """Test updating block_type succeeds."""
        block = await create_test_block(
            db_session, year=2025, name="Test", block_type="holiday"
        )

        response = await client.patch(
            f"/api/v1/admin/blocks/{block.id}",
            cookies={"admin_session": admin_session_cookie},
            json={"block_type": "school_holiday"},
        )

        assert response.status_code == HTTP_200_OK
        data = response.json()
        assert data["block_type"] == "school_holiday"

    async def test_update_nonexistent_block(
        self, client: AsyncClient, admin_session_cookie: str
    ) -> None:
        """Test updating non-existent block returns 404."""
        response = await client.patch(
            "/api/v1/admin/blocks/00000000-0000-0000-0000-000000000000",
            cookies={"admin_session": admin_session_cookie},
            json={"name": "Updated"},
        )
        assert response.status_code == HTTP_404_NOT_FOUND
