#!/usr/bin/env python3
"""
Database Initialization Script

Initializes a fresh database with the current schema using Alembic migrations.
This is the recommended way to set up a new database instance.

Usage:
    python scripts/db_init.py [--drop-all] [--seed] [--database-url URL]

Options:
    --drop-all      Drop all existing tables before initialization (DANGEROUS!)
    --seed          Seed with sample data after initialization
    --database-url  Override DATABASE_URL from environment
    --help          Show this help message

Examples:
    # Initialize new database
    python scripts/db_init.py

    # Initialize and seed sample data
    python scripts/db_init.py --seed

    # Fresh start (WARNING: destroys existing data)
    python scripts/db_init.py --drop-all --seed

Environment Variables:
    DATABASE_URL    PostgreSQL connection string (required if not passed via --database-url)
    LITESTAR_APP    Application path (default: app.server.asgi:create_app)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def load_env_file():
    """Load DATABASE_URL from .env file if not in environment."""
    if os.environ.get("DATABASE_URL"):
        return

    # Check backend/.env first, then root .env
    backend_env = Path(__file__).parents[1] / "backend" / ".env"
    root_env = Path(__file__).parents[1] / ".env"

    for env_path in (backend_env, root_env):
        if not env_path.exists():
            continue
        
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            
            key, value = line.split("=", 1)
            if key.strip() == "DATABASE_URL":
                os.environ["DATABASE_URL"] = value.strip().strip('"').strip("'")
                print(f"✓ Loaded DATABASE_URL from {env_path}")
                return


def check_database_connection(database_url: str) -> bool:
    """Verify database is accessible."""
    try:
        import psycopg
        # Normalize URL for psycopg
        normalized_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        normalized_url = normalized_url.replace("postgresql+psycopg://", "postgresql://")
        
        with psycopg.connect(normalized_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                print(f"✓ Database connection successful")
                print(f"  PostgreSQL version: {version.split(',')[0]}")
                return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}", file=sys.stderr)
        return False


def drop_all_tables(database_url: str):
    """Drop all tables in the database (DANGEROUS!)."""
    import psycopg
    
    normalized_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    normalized_url = normalized_url.replace("postgresql+psycopg://", "postgresql://")
    
    print("\n⚠️  WARNING: Dropping all tables...")
    
    with psycopg.connect(normalized_url) as conn:
        with conn.cursor() as cur:
            # Get all tables
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = [row[0] for row in cur.fetchall()]
            
            if not tables:
                print("  No tables to drop")
                return
            
            print(f"  Dropping {len(tables)} tables...")
            cur.execute("DROP TABLE IF EXISTS " + ", ".join(tables) + " CASCADE")
            conn.commit()
            print("✓ All tables dropped")


def run_migrations():
    """Run Alembic migrations to create schema."""
    print("\n🔄 Running database migrations...")
    
    # Set up environment
    env = os.environ.copy()
    env.setdefault("LITESTAR_APP", "app.server.asgi:create_app")
    
    # Change to backend directory for Alembic
    backend_dir = Path(__file__).parents[1] / "backend"
    
    try:
        result = subprocess.run(
            ["uv", "run", "litestar", "database", "upgrade", "--no-prompt"],
            cwd=backend_dir,
            env=env,
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Migrations completed successfully")
        if result.stdout:
            for line in result.stdout.splitlines():
                if line.strip():
                    print(f"  {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Migration failed: {e}", file=sys.stderr)
        if e.stdout:
            print("STDOUT:", e.stdout, file=sys.stderr)
        if e.stderr:
            print("STDERR:", e.stderr, file=sys.stderr)
        return False


def seed_database():
    """Seed database with sample data."""
    print("\n🌱 Seeding database with sample data...")
    
    backend_dir = Path(__file__).parents[1] / "backend"
    seed_script = Path(__file__).parent / "seed.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(seed_script)],
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True
        )
        print("✓ Database seeded successfully")
        if result.stdout:
            print(f"  {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Seeding failed: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize database with schema migrations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--drop-all",
        action="store_true",
        help="Drop all existing tables before initialization (DANGEROUS!)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed with sample data after initialization"
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection string (overrides DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_env_file()
    
    # Get database URL
    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL must be provided via --database-url or environment variable", file=sys.stderr)
        print("\nSet DATABASE_URL in backend/.env or root .env file, or pass --database-url", file=sys.stderr)
        sys.exit(1)
    
    # Set in environment for child processes
    os.environ["DATABASE_URL"] = database_url
    
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    
    # Check database connection
    if not check_database_connection(database_url):
        print("\n✗ Cannot proceed without database connection", file=sys.stderr)
        sys.exit(1)
    
    # Drop tables if requested
    if args.drop_all:
        response = input("\n⚠️  Are you sure you want to DROP ALL TABLES? Type 'yes' to confirm: ")
        if response.lower() != "yes":
            print("Aborted.")
            sys.exit(0)
        drop_all_tables(database_url)
    
    # Run migrations
    if not run_migrations():
        print("\n✗ Initialization failed during migrations", file=sys.stderr)
        sys.exit(1)
    
    # Seed if requested
    if args.seed:
        if not seed_database():
            print("\n⚠️  Warning: Seeding failed, but schema is initialized", file=sys.stderr)
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    
    if args.seed:
        print("\n📊 Sample data has been loaded.")
    
    print("\nNext steps:")
    print("  - Start the backend: cd backend && uv run litestar run --reload")
    print("  - View API docs: http://localhost:8000/docs")


if __name__ == "__main__":
    main()
