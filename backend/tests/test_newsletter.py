"""Tests for newsletter integration functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.anyio


async def test_newsletter_subscription_with_configured_webhook(mocker):
    """Test newsletter subscription when webhook is configured."""

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"members": [{"id": "123"}]}
    mock_response.raise_for_status = MagicMock()

    # Create mock for the post method
    mock_post = AsyncMock(return_value=mock_response)

    # Create mock client instance to be returned from __aenter__
    mock_client = MagicMock()
    mock_client.post = mock_post

    # Mock the AsyncClient as a callable that returns an async context manager
    mock_async_client_class = MagicMock()
    mock_async_client_context = MagicMock()
    mock_async_client_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client_context.__aexit__ = AsyncMock(return_value=None)
    mock_async_client_class.return_value = mock_async_client_context

    mocker.patch("httpx.AsyncClient", mock_async_client_class)
    mocker.patch(
        "app.lib.newsletter.settings.newsletter_webhook_url",
        "https://example.com/ghost/api/admin",
    )
    mocker.patch(
        "app.lib.newsletter.settings.newsletter_webhook_token",
        "test_key_id:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",  # noqa: E501
    )
    mocker.patch("app.lib.newsletter.settings.email_dry_run", False)

    from app.lib.newsletter import notify_newsletter_subscription

    # Call newsletter subscription
    await notify_newsletter_subscription(email="test@example.com", name="Test User")

    # Verify HTTP POST was called
    assert mock_post.called, "Expected mock_post to be called"
    call_args = mock_post.call_args

    # Verify URL
    assert "ghost/api/admin/members" in call_args[0][0]

    # Verify payload
    payload = call_args[1]["json"]
    assert "members" in payload
    assert payload["members"][0]["email"] == "test@example.com"
    assert payload["members"][0]["name"] == "Test User"


async def test_newsletter_subscription_without_webhook(mocker):
    """Test newsletter subscription when webhook is not configured."""

    mocker.patch("app.lib.newsletter.settings.newsletter_webhook_url", "")

    mock_client_class = AsyncMock()
    mocker.patch("httpx.AsyncClient", return_value=mock_client_class)

    from app.lib.newsletter import notify_newsletter_subscription

    # Call newsletter subscription
    await notify_newsletter_subscription(email="test@example.com", name="Test User")

    # HTTP client should not be called (webhook not configured)
    assert not mock_client_class.called


async def test_newsletter_worker_task_without_webhook(mocker):
    """Test newsletter subscription worker task when webhook is not configured."""

    # Create a simple context mock
    ctx_mock = mocker.MagicMock()

    # Patch at the point of import/use
    with patch("app.lib.newsletter.notify_newsletter_subscription") as mock_notify:
        mock_notify.return_value = None  # Function is async and returns None

        from app.lib.worker import notify_newsletter_subscription_task

        # Call worker task
        result = await notify_newsletter_subscription_task(
            ctx_mock, email="test@example.com", name="Test User"
        )

        # Verify notify function was called
        mock_notify.assert_called_once_with(email="test@example.com", name="Test User")

        # Verify result structure
        assert "email" in result
        assert result["email"] == "test@example.com"
        assert "sent_at" in result
