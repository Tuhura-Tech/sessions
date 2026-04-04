from __future__ import annotations

from collections import defaultdict

from advanced_alchemy.extensions.litestar import service
from litestar.exceptions import ValidationException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.block import Block as BlockModel
from app.db.models.block_link import BlockLink as BlockLinkModel
from app.domains.public.schemas.session import Location, Session
from app.domains.public.services.session import SessionService


def validate_limit_offset(limit: int | None, offset: int | None) -> None:
    if limit is not None and limit < 0:
        raise ValidationException(detail="limit must be >= 0")
    if offset is not None and offset < 0:
        raise ValidationException(detail="offset must be >= 0")


async def build_session_list_response(
    *,
    sessions_service: SessionService,
    db_session: AsyncSession,
    filters: list,
    limit: int | None,
    offset: int | None,
) -> service.OffsetPagination[Session]:
    if limit is not None or offset is not None:
        from advanced_alchemy.filters import LimitOffset

        filters.append(LimitOffset(limit=limit or 0, offset=offset or 0))

    results, total = await sessions_service.list_and_count(*filters)

    blocks_by_session = defaultdict(list)
    if results:
        block_res = await db_session.execute(
            select(BlockLinkModel.session_id, BlockModel.name)
            .join(BlockModel, BlockModel.id == BlockLinkModel.block_id)
            .where(BlockLinkModel.session_id.in_([s.id for s in results]))
        )
        for session_id, block_name in block_res.all():
            blocks_by_session[str(session_id)].append(block_name)

    schemas = []
    for result in results:
        location = Location(
            name=result.location.name,
            address=result.location.address,
            region=result.location.region,
            lat=result.location.lat,
            lng=result.location.lng,
        )
        schema = Session(
            id=result.id,
            name=result.name,
            year=result.year,
            session_type=result.session_type,
            age_lower=result.age_lower,
            age_upper=result.age_upper,
            day_of_week=result.day_of_week,
            start_time=result.start_time,
            end_time=result.end_time,
            waitlist=getattr(result, "is_full", False),
            description=result.description,
            blocks=blocks_by_session.get(str(result.id), []),
            location=location,
        )
        schemas.append(schema)

    return service.OffsetPagination(
        items=schemas,
        limit=limit or 0,
        offset=offset or 0,
        total=total,
    )
