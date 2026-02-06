from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING


def setup_environment() -> None:
    """Configure the environment variables and path."""
    current_path = Path(__file__).parent.parent.resolve()
    sys.path.append(str(current_path))

    os.environ.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
    os.environ.setdefault("LITESTAR_APP_NAME", "Sessions API")
    os.environ.setdefault("LITESTAR_GRANIAN_IN_SUBPROCESS", "false")
    os.environ.setdefault("LITESTAR_GRANIAN_USE_LITESTAR_LOGGER", "true")


def run_cli() -> None:
    """Application Entrypoint.

    This function sets up the environment and runs the Litestar CLI.
    If there's an error loading the required libraries, it will exit with a status code of 1.
    """
    setup_environment()

    from litestar.cli.main import litestar_group

    litestar_group()


if __name__ == "__main__":
    run_cli()