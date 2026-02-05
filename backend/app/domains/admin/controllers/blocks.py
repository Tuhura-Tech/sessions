from __future__ import annotations

import logging
from uuid import UUID

from advanced_alchemy.extensions.litestar import providers, service
from advanced_alchemy.filters import LimitOffset
from litestar import Controller, get, patch, post
from litestar.exceptions import NotFoundException
from litestar.status_codes import HTTP_200_OK

from app.domains.admin.schemas.block import Block, BlockCreate, BlockUpdate
from app.domains.admin.guards import admin_session_guard
from app.domains.admin.services.block import BlockService

logger = logging.getLogger(__name__)


class BlockController(Controller):
    """Public endpoints for caregivers (no auth required)."""

    path = "/api/v1/admin/blocks"
    tags = ["Admin"]
    guards = [admin_session_guard]
    dependencies = providers.create_service_dependencies(
        BlockService,
        "block_service",
    )

    @get("/", status_code=HTTP_200_OK, summary="List blocks")
    async def list_blocks(
        self,
        block_service: BlockService,
        limit: int = 100,
        offset: int = 0,
    ) -> service.OffsetPagination[Block]:
        """List all blocks with pagination.

        Args:
            limit: Maximum number of results to return (default: 100)
            offset: Number of results to skip (default: 0)
        """
        results, total = await block_service.list_and_count(LimitOffset(limit, offset))
        return block_service.to_schema(results, total, schema_type=Block)

    @post("/")
    async def create_block(
        self,
        block_service: BlockService,
        data: BlockCreate,
    ) -> Block:
        """Create a new block."""
        blk = await block_service.create(data)
        return block_service.to_schema(blk, schema_type=Block)

    @get("/{block_id:uuid}", status_code=HTTP_200_OK, summary="Get block by ID")
    async def get_block(
        self,
        block_service: BlockService,
        block_id: UUID,
    ) -> Block:
        """Get a specific block by ID."""
        blk = await block_service.get(block_id)
        if not blk:
            raise NotFoundException(detail="Block not found")

        return block_service.to_schema(blk, schema_type=Block)

    @patch("/{block_id:uuid}", status_code=HTTP_200_OK, summary="Update block")
    async def update_block(
        self,
        block_service: BlockService,
        block_id: UUID,
        data: BlockUpdate,
    ) -> Block:
        """Update an existing block."""
        blk = await block_service.update(data.model_dump(exclude_unset=True), block_id)
        if not blk:
            raise NotFoundException(detail="Block not found")
        return block_service.to_schema(blk, schema_type=Block)
