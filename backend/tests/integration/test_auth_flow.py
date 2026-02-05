"""
Integration tests for authentication flow using database fixtures.

These tests use the db_session fixture to directly interact with the database,
testing the authentication service layer and model interactions.
Uses SQLite in-memory by default for speed, or PostgreSQL if TEST_DATABASE_URL is set.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.db.models import Caregiver, CaregiverMagicLink, CaregiverSession
from app.lib.auth import (
    new_token,
    hash_token,
    utcnow,
    magic_link_expires_at,
    session_expires_at,
)


pytestmark = [pytest.mark.anyio, pytest.mark.integration]


@pytest.mark.auth
class TestMagicLinkModel:
    """Test CaregiverMagicLink model interactions."""

    async def test_create_magic_link(self, db_session: AsyncSession):
        """Test creating a magic link in the database."""
        # Create a caregiver first
        caregiver = Caregiver(email="test@example.com")
        db_session.add(caregiver)
        await db_session.flush()  # Get the ID without committing

        # Create a magic link
        token = new_token()
        token_hash = hash_token(token)
        expires_at = magic_link_expires_at()

        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Verify it was created
        assert magic_link.id is not None
        assert magic_link.caregiver_id == caregiver.id
        assert magic_link.token_hash == token_hash
        assert magic_link.expires_at == expires_at

    async def test_find_magic_link_by_hash(self, db_session: AsyncSession):
        """Test finding a magic link by its hash."""
        # Create caregiver and magic link
        caregiver = Caregiver(email="find@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        token = new_token()
        token_hash = hash_token(token)

        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=token_hash,
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Find it by hash
        result = await db_session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.token_hash == token_hash
            )
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.id == magic_link.id
        assert found.token_hash == token_hash

    async def test_magic_link_expiration_check(self, db_session: AsyncSession):
        """Test checking if a magic link is expired."""
        caregiver = Caregiver(email="expired@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Create an expired link
        past_time = utcnow() - timedelta(hours=1)
        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=past_time,
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Check expiration
        now = utcnow()
        is_expired = now > magic_link.expires_at

        assert is_expired is True

    async def test_magic_link_not_expired(self, db_session: AsyncSession):
        """Test that a valid magic link is not expired."""
        caregiver = Caregiver(email="valid@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Create a valid link
        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Check expiration
        now = utcnow()
        is_expired = now > magic_link.expires_at

        assert is_expired is False

    async def test_mark_magic_link_as_used(self, db_session: AsyncSession):
        """Test marking a magic link as used."""
        caregiver = Caregiver(email="used@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Mark as used
        magic_link.used_at = utcnow()
        await db_session.flush()

        # Verify
        result = await db_session.execute(
            select(CaregiverMagicLink).where(CaregiverMagicLink.id == magic_link.id)
        )
        found = result.scalar_one()
        assert found.used_at is not None

    async def test_cannot_reuse_magic_link(self, db_session: AsyncSession):
        """Test that a used magic link cannot be reused."""
        caregiver = Caregiver(email="noreuse@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Mark as used
        magic_link.used_at = utcnow()
        await db_session.flush()

        # Try to use again
        is_usable = magic_link.used_at is None
        assert is_usable is False


pytestmark = [pytest.mark.anyio, pytest.mark.integration, pytest.mark.auth]


class TestCaregiverSessionModel:
    """Test CaregiverSession model interactions."""

    async def test_create_session(self, db_session: AsyncSession):
        """Test creating a caregiver session."""
        caregiver = Caregiver(email="session@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Create session
        session_token = new_token()
        session_hash = hash_token(session_token)

        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=session_hash,
            expires_at=session_expires_at(),
        )
        db_session.add(session)
        await db_session.flush()

        # Verify
        assert session.id is not None
        assert session.caregiver_id == caregiver.id
        assert session.token_hash == session_hash

    async def test_find_session_by_hash(self, db_session: AsyncSession):
        """Test finding a session by its hash."""
        caregiver = Caregiver(email="findsession@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        session_hash = hash_token(new_token())
        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=session_hash,
            expires_at=session_expires_at(),
        )
        db_session.add(session)
        await db_session.flush()

        # Find by hash
        result = await db_session.execute(
            select(CaregiverSession).where(CaregiverSession.token_hash == session_hash)
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.token_hash == session_hash

    async def test_session_expiration(self, db_session: AsyncSession):
        """Test checking if a session is expired."""
        caregiver = Caregiver(email="expiredsession@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Create expired session
        past_time = utcnow() - timedelta(days=31)
        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=past_time,
        )
        db_session.add(session)
        await db_session.flush()

        # Check expiration
        is_expired = utcnow() > session.expires_at
        assert is_expired is True

    async def test_session_not_expired(self, db_session: AsyncSession):
        """Test that a valid session is not expired."""
        caregiver = Caregiver(email="validsession@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=session_expires_at(),
        )
        db_session.add(session)
        await db_session.flush()

        is_expired = utcnow() > session.expires_at
        assert is_expired is False

    async def test_revoke_session(self, db_session: AsyncSession):
        """Test revoking a session."""
        caregiver = Caregiver(email="revoke@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=session_expires_at(),
        )
        db_session.add(session)
        await db_session.flush()

        # Revoke by setting expires_at to past
        session.expires_at = utcnow() - timedelta(seconds=1)
        await db_session.flush()

        # Verify revoked
        is_expired = utcnow() > session.expires_at
        assert is_expired is True


@pytest.mark.integration
@pytest.mark.auth
class TestCaregiverModel:
    """Test Caregiver model interactions."""

    async def test_create_caregiver(self, db_session: AsyncSession):
        """Test creating a caregiver."""
        caregiver = Caregiver(email="test@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        assert caregiver.id is not None
        assert caregiver.email == "test@example.com"

    async def test_find_caregiver_by_email(self, db_session: AsyncSession):
        """Test finding a caregiver by email."""
        email = "find@example.com"
        caregiver = Caregiver(email=email)
        db_session.add(caregiver)
        await db_session.flush()

        # Find by email
        result = await db_session.execute(
            select(Caregiver).where(Caregiver.email == email)
        )
        found = result.scalar_one_or_none()

        assert found is not None
        assert found.email == email
        assert found.id == caregiver.id

    async def test_caregiver_email_unique(self, db_session: AsyncSession):
        """Test that caregiver emails are unique."""
        email = "unique@example.com"

        caregiver1 = Caregiver(email=email)
        db_session.add(caregiver1)
        await db_session.flush()

        # Try to create another with same email
        caregiver2 = Caregiver(email=email)
        db_session.add(caregiver2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(Exception):  # IntegrityError
            await db_session.flush()

    async def test_caregiver_relationships(self, db_session: AsyncSession):
        """Test caregiver relationships with magic links and sessions."""
        caregiver = Caregiver(email="relationships@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Add magic links
        for i in range(3):
            magic_link = CaregiverMagicLink(
                caregiver_id=caregiver.id,
                token_hash=hash_token(new_token()),
                expires_at=magic_link_expires_at(),
            )
            db_session.add(magic_link)

        # Add sessions
        for i in range(2):
            session = CaregiverSession(
                caregiver_id=caregiver.id,
                token_hash=hash_token(new_token()),
                expires_at=session_expires_at(),
            )
            db_session.add(session)

        await db_session.flush()

        # Verify relationships (if ORM relationships are defined)
        # This depends on the actual model definitions


@pytest.mark.integration
@pytest.mark.auth
class TestAuthenticationWorkflow:
    """Test complete authentication workflows using database."""

    async def test_complete_auth_flow_database(self, db_session: AsyncSession):
        """Test complete authentication flow at database level."""
        # 1. Create caregiver
        email = "workflow@example.com"
        caregiver = Caregiver(email=email)
        db_session.add(caregiver)
        await db_session.flush()

        # 2. Create magic link
        token = new_token()
        token_hash = hash_token(token)
        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=token_hash,
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # 3. Verify magic link exists and is valid
        result = await db_session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.token_hash == token_hash
            )
        )
        found_link = result.scalar_one()
        assert found_link.used_at is None  # Not used yet
        assert utcnow() < found_link.expires_at  # Not expired

        # 4. Mark magic link as used
        found_link.used_at = utcnow()
        await db_session.flush()

        # 5. Create session
        session_token = new_token()
        session_hash = hash_token(session_token)
        session = CaregiverSession(
            caregiver_id=caregiver.id,
            token_hash=session_hash,
            expires_at=session_expires_at(),
        )
        db_session.add(session)
        await db_session.flush()

        # 6. Verify session is valid
        result = await db_session.execute(
            select(CaregiverSession).where(CaregiverSession.token_hash == session_hash)
        )
        found_session = result.scalar_one()
        assert utcnow() < found_session.expires_at

    async def test_prevent_magic_link_reuse(self, db_session: AsyncSession):
        """Test that magic links cannot be reused."""
        caregiver = Caregiver(email="noreuse@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        token = new_token()
        token_hash = hash_token(token)
        magic_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=token_hash,
            expires_at=magic_link_expires_at(),
        )
        db_session.add(magic_link)
        await db_session.flush()

        # Use the link
        magic_link.used_at = utcnow()
        await db_session.flush()

        # Try to verify it can't be used again
        result = await db_session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.token_hash == token_hash
            )
        )
        found = result.scalar_one()
        can_use = found.used_at is None and utcnow() < found.expires_at

        assert can_use is False

    async def test_cleanup_expired_links(self, db_session: AsyncSession):
        """Test finding and potentially cleaning up expired links."""
        caregiver = Caregiver(email="cleanup@example.com")
        db_session.add(caregiver)
        await db_session.flush()

        # Create mix of valid and expired links
        valid_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=magic_link_expires_at(),  # Valid
        )

        expired_link = CaregiverMagicLink(
            caregiver_id=caregiver.id,
            token_hash=hash_token(new_token()),
            expires_at=utcnow() - timedelta(hours=1),  # Expired
        )

        db_session.add(valid_link)
        db_session.add(expired_link)
        await db_session.flush()

        # Find expired links
        result = await db_session.execute(
            select(CaregiverMagicLink).where(
                CaregiverMagicLink.caregiver_id == caregiver.id,
                CaregiverMagicLink.expires_at < utcnow(),
            )
        )
        expired_links = result.scalars().all()

        assert len(expired_links) == 1
        assert expired_links[0].id == expired_link.id
