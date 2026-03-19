"""Unit tests for admin locations controller."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from advanced_alchemy.exceptions import NotFoundError as AlchemyNotFoundError
from litestar.exceptions import NotFoundException
from advanced_alchemy.extensions.litestar import service as alchemy_service

from app.domains.admin.controllers.locations import LocationController
from app.domains.admin.schemas.location import LocationCreate, LocationUpdate
from app.db import models as m


def make_controller() -> LocationController:
    """Create a controller instance for testing."""
    return LocationController(owner=SimpleNamespace())


class DummyLocationService:
    """Dummy location service for unit testing."""

    def __init__(self):
        self.mock_locations = [
            m.Location(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                name="Test Location 1",
                address="123 Test St",
                region="Test Region",
                lat=-41.2865,
                lng=174.7762,
                contact_name="Test Contact",
                contact_email="contact@example.com",
            ),
            m.Location(
                id=UUID("22222222-2222-2222-2222-222222222222"),
                name="Test Location 2",
                address="456 Test Ave",
                region="Another Region",
                lat=-41.2900,
                lng=174.7800,
                contact_name="Another Contact",
                contact_email="another@example.com",
            ),
        ]

    async def list_and_count(
        self, *args: Any, **kwargs: Any
    ) -> tuple[list[m.Location], int]:
        """Return all locations with count."""
        return self.mock_locations, len(self.mock_locations)

    async def create(self, data: LocationCreate) -> m.Location:
        """Create a new location."""
        new_location = m.Location(
            id=UUID("33333333-3333-3333-3333-333333333333"),
            name=data.name,
            address=data.address,
            region=data.region,
            lat=data.lat,
            lng=data.lng,
            contact_name=data.contact_name,
            contact_email=data.contact_email,
        )
        self.mock_locations.append(new_location)
        return new_location

    async def get(self, location_id: UUID) -> m.Location | None:
        """Get location by ID.

        Returns None for simple get calls, raises AlchemyNotFoundError for service calls
        that expect exceptions (like in get_location_sessions).
        """
        for loc in self.mock_locations:
            if loc.id == location_id:
                return loc
        # For now, return None - but subclass or configure if exception needed
        return None

    async def update(self, data: dict[str, Any], location_id: UUID) -> m.Location:
        """Update a location."""
        location = await self.get(location_id)
        if location is None:
            raise AlchemyNotFoundError("Location not found")
        for key, value in data.items():
            setattr(location, key, value)
        return location

    def to_schema(
        self, data: Any, total: int | None = None, *args: Any, **kwargs: Any
    ) -> Any:
        """Convert ORM model to schema (with pagination support)."""
        if total is not None:
            # Return OffsetPagination for list endpoints
            return alchemy_service.OffsetPagination(
                items=data, total=total, limit=100, offset=0
            )
        return data


class DummyLocationServiceWithExceptions(DummyLocationService):
    """Location service that raises exceptions on not found (for testing exception handling)."""

    async def get(self, location_id: UUID) -> m.Location:
        """Get location by ID, raise exception if not found."""
        for loc in self.mock_locations:
            if loc.id == location_id:
                return loc
        raise AlchemyNotFoundError("Location not found")


class DummySessionService:
    """Dummy session service for unit testing."""

    def __init__(self):
        self.mock_sessions = [
            m.Session(
                id=UUID("44444444-4444-4444-4444-444444444444"),
                name="Test Session 1",
                location_id=UUID("11111111-1111-1111-1111-111111111111"),
                archived=False,
            ),
            m.Session(
                id=UUID("55555555-5555-5555-5555-555555555555"),
                name="Test Session 2",
                location_id=UUID("11111111-1111-1111-1111-111111111111"),
                archived=False,
            ),
            m.Session(
                id=UUID("66666666-6666-6666-6666-666666666666"),
                name="Archived Session",
                location_id=UUID("11111111-1111-1111-1111-111111111111"),
                archived=True,
            ),
        ]

    async def list_and_count(
        self, *filters: Any, **kwargs: Any
    ) -> tuple[list[m.Session], int]:
        """Return sessions matching filters.

        Simple filter logic:
        - If only 1 filter: return all sessions for the location (including archived)
        - If 2 filters: return only non-archived sessions for the location
        """
        # Always filter by location_id (first filter)
        # Second filter (if present) is ~archived
        filtered = self.mock_sessions

        # Extract location_id from first filter
        if len(filters) > 0 and hasattr(filters[0], "right"):
            location_id = filters[0].right.value
            filtered = [s for s in filtered if s.location_id == location_id]

        # If there are 2 filters, exclude archived
        if len(filters) == 2:
            filtered = [s for s in filtered if not s.archived]

        return filtered, len(filtered)

    def to_schema(
        self, data: Any, total: int | None = None, *args: Any, **kwargs: Any
    ) -> Any:
        """Convert ORM model to schema (with pagination support)."""
        if total is not None:
            # Return OffsetPagination for list endpoints
            return alchemy_service.OffsetPagination(
                items=data, total=total, limit=100, offset=0
            )
        return data


class TestLocationController:
    """Unit tests for LocationController."""

    @pytest.mark.anyio
    async def test_list_locations(self):
        """Test listing locations with pagination."""
        controller = make_controller()
        service = DummyLocationService()

        result = await LocationController.list_locations.fn(
            controller,
            location_service=service,
            limit=100,
            offset=0,
        )

        # Result should be OffsetPagination
        assert isinstance(result, alchemy_service.OffsetPagination)
        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].name == "Test Location 1"
        assert result.items[1].name == "Test Location 2"

    @pytest.mark.anyio
    async def test_create_location(self):
        """Test creating a new location."""
        controller = make_controller()
        service = DummyLocationService()

        data = LocationCreate(
            name="New Location",
            address="789 New St",
            region="New Region",
            lat=-41.2950,
            lng=174.7850,
            contact_name="New Contact",
            contact_email="new@example.com",
        )

        result = await LocationController.create_location.fn(
            controller,
            location_service=service,
            data=data,
        )

        assert result.name == "New Location"
        assert result.address == "789 New St"
        assert result.region == "New Region"
        assert result.lat == -41.2950
        assert result.lng == 174.7850
        assert result.contact_name == "New Contact"
        assert result.contact_email == "new@example.com"

    @pytest.mark.anyio
    async def test_get_location_success(self):
        """Test getting a location by ID."""
        controller = make_controller()
        service = DummyLocationService()

        location_id = UUID("11111111-1111-1111-1111-111111111111")
        result = await LocationController.get_location.fn(
            controller,
            location_service=service,
            location_id=location_id,
        )

        assert result.id == location_id
        assert result.name == "Test Location 1"

    @pytest.mark.anyio
    async def test_get_location_not_found(self):
        """Test getting a non-existent location."""
        controller = make_controller()
        service = DummyLocationService()

        location_id = UUID("99999999-9999-9999-9999-999999999999")

        with pytest.raises(NotFoundException, match="Location not found"):
            await LocationController.get_location.fn(
                controller,
                location_service=service,
                location_id=location_id,
            )

    @pytest.mark.anyio
    async def test_update_location_success(self):
        """Test updating a location."""
        controller = make_controller()
        service = DummyLocationService()

        location_id = UUID("11111111-1111-1111-1111-111111111111")
        data = LocationUpdate(name="Updated Location", address="Updated Address")

        result = await LocationController.update_location.fn(
            controller,
            location_service=service,
            location_id=location_id,
            data=data,
        )

        assert result.id == location_id
        assert result.name == "Updated Location"
        assert result.address == "Updated Address"

    @pytest.mark.anyio
    async def test_update_location_not_found(self):
        """Test updating a non-existent location."""
        controller = make_controller()
        service = DummyLocationService()

        location_id = UUID("99999999-9999-9999-9999-999999999999")
        data = LocationUpdate(name="Updated Location")

        with pytest.raises(NotFoundException, match="Location not found"):
            await LocationController.update_location.fn(
                controller,
                location_service=service,
                location_id=location_id,
                data=data,
            )

    @pytest.mark.anyio
    async def test_get_location_sessions_success(self):
        """Test getting sessions for a location."""
        controller = make_controller()
        location_service = DummyLocationService()
        session_service = DummySessionService()

        location_id = UUID("11111111-1111-1111-1111-111111111111")

        result = await LocationController.get_location_sessions.fn(
            controller,
            location_id=location_id,
            location_service=location_service,
            session_service=session_service,
            include_archived=False,
        )

        # Result is OffsetPagination
        assert isinstance(result, alchemy_service.OffsetPagination)
        assert result.total == 2  # Only non-archived sessions
        assert len(result.items) == 2
        assert all(not s.archived for s in result.items)

    @pytest.mark.anyio
    async def test_get_location_sessions_include_archived(self):
        """Test getting sessions for a location including archived."""
        controller = make_controller()
        location_service = DummyLocationService()
        session_service = DummySessionService()

        location_id = UUID("11111111-1111-1111-1111-111111111111")

        result = await LocationController.get_location_sessions.fn(
            controller,
            location_id=location_id,
            location_service=location_service,
            session_service=session_service,
            include_archived=True,
        )

        assert isinstance(result, alchemy_service.OffsetPagination)
        assert result.total == 3  # All sessions including archived
        assert len(result.items) == 3

    @pytest.mark.anyio
    async def test_get_location_sessions_location_not_found(self):
        """Test getting sessions for a non-existent location."""
        controller = make_controller()
        location_service = DummyLocationServiceWithExceptions()
        session_service = DummySessionService()

        location_id = UUID("99999999-9999-9999-9999-999999999999")

        with pytest.raises(NotFoundException, match="Location not found"):
            await LocationController.get_location_sessions.fn(
                controller,
                location_id=location_id,
                location_service=location_service,
                session_service=session_service,
                include_archived=False,
            )
