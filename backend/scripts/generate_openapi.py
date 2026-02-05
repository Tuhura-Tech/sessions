#!/usr/bin/env python3
"""Generate OpenAPI schema from the Litestar application."""

import asyncio
import json
import sys
from pathlib import Path

import yaml

# Add the backend directory to the path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def generate_schema():
    """Generate and save the OpenAPI schema."""
    # Import after environment is set
    from app.server.asgi import create_app

    app = create_app()

    # Get the OpenAPI schema
    schema = app.openapi_schema

    # Save as YAML
    docs_dir = Path(__file__).parent.parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    yaml_path = docs_dir / "schema.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(schema.to_schema(), f, default_flow_style=False, sort_keys=False)

    print(f"✓ OpenAPI schema saved to {yaml_path}")

    # Also save as JSON for potential use with validation tools
    json_path = docs_dir / "schema.json"
    with open(json_path, "w") as f:
        json.dump(schema.to_schema(), f, indent=2)

    print(f"✓ OpenAPI schema saved to {json_path}")


if __name__ == "__main__":
    asyncio.run(generate_schema())
