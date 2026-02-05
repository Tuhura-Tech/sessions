"""
Integration tests for public health endpoints.

Tests for health check endpoints that monitor API status and availability.
"""

import pytest
from litestar.status_codes import HTTP_200_OK
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.endpoints,
]


class TestHealthEndpoints:
    """Test public health check endpoints."""

    async def test_health_check(self, client):
        """Test GET /api/v1/health endpoint exists and is callable."""
        response = await client.get("/api/v1/health")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert "status" in data
        assert data["status"] is True  # Boolean, not string
        assert "timestamp" in data
        assert "version" in data
        assert "service" in data
        assert "debug" in data

    async def test_readiness_check(self, client):
        """Test GET /api/v1/health/ready returns readiness."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert "ready" in data
        assert data["ready"] is True
        assert "timestamp" in data

    async def test_liveness_check(self, client):
        """Test GET /api/v1/health/live returns liveness."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert "alive" in data
        assert data["alive"] is True
        assert "timestamp" in data

    async def test_health_check_timestamp_format(self, client):
        """Test health check timestamp is ISO format."""
        response = await client.get("/api/v1/health")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert "timestamp" in data
        # Should be ISO 8601 format
        from datetime import datetime

        datetime.fromisoformat(data["timestamp"])

    async def test_health_check_service_info(self, client):
        """Test health check returns correct service information."""
        response = await client.get("/api/v1/health")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        assert data["service"] == "tuhura-sessions-api"
        assert data["version"] == "1.0.0"

    async def test_readiness_check_timestamp(self, client):
        """Test readiness check timestamp is ISO format."""
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        from datetime import datetime

        datetime.fromisoformat(data["timestamp"])

    async def test_liveness_check_timestamp(self, client):
        """Test liveness check timestamp is ISO format."""
        response = await client.get("/api/v1/health/live")
        assert response.status_code == HTTP_200_OK

        data = response.json()
        from datetime import datetime

        datetime.fromisoformat(data["timestamp"])
