from __future__ import annotations

import logging

from advanced_alchemy.extensions.litestar import providers, service
from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK

from app.domains.public.schemas.block import Block
from app.domains.public.services.block import BlockService

logger = logging.getLogger(__name__)


class PublicBlockController(Controller):
    """Public endpoints for blocks (no auth required)."""

    path = "/api/v1/blocks"
    tags = ["Public"]
    dependencies = providers.create_service_dependencies(
        BlockService,
        "block_service",
    )

    @get("/", status_code=HTTP_200_OK, summary="List blocks")
    async def list_blocks(
        self,
        block_service: BlockService,
    ) -> service.OffsetPagination[Block]:
        """List all blocks for current and upcoming years.

        Returns blocks that can be used for term date lookups.
        """
        results, total = await block_service.list_and_count()
        return block_service.to_schema(results, schema_type=Block)
