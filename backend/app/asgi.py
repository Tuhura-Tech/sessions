# from __future__ import annotations

# from typing import TYPE_CHECKING

from litestar import Litestar


def create_app() -> Litestar:
    """Create ASGI application.

    Returns:
        The ASGI application.
    """
    # from litestar_saq.config import QueueConfig

    # QueueConfig._POOL_KWARGS = {"autocommit": True}

    from app.server.core import ApplicationCore

    return Litestar(plugins=[ApplicationCore()])
