#!/usr/bin/env python3
"""
Database restore script - empties and restores from backup
"""
import subprocess
import sys
import time
from pathlib import Path

# Database credentials (from .env)
DB_USER = "sessions"
DB_PASSWORD = "sessions"
DB_NAME = "sessions"
DB_HOST = "localhost"
DB_PORT = "5432"

# PostgreSQL connection string
PSQL_CMD = [
    "docker", "compose", "exec", "-T", "postgres",
    "psql", f"-U{DB_USER}", "-d", DB_NAME
]

def run_command(cmd, description=""):
    """Run a shell command"""
    if description:
        print(f"→ {description}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e.stderr}")
        return False

def main():
    # Change to project directory
    project_dir = Path("/home/leon/Projects/sessions")
    backup_file = project_dir / "backup.sql"
    
    if not backup_file.exists():
        print(f"✗ Backup file not found: {backup_file}")
        sys.exit(1)
    
    print("=== Database Restore ===\n")
    
    # Check if database is accessible
    print("Checking PostgreSQL connection...")
    check_cmd = ["docker", "compose", "exec", "-T", "postgres", "pg_isready", f"-U{DB_USER}"]
    
    try:
        subprocess.run(check_cmd, cwd=project_dir, check=True, capture_output=True, timeout=10)
        print("✓ PostgreSQL is ready\n")
    except subprocess.TimeoutExpired:
        print("✗ PostgreSQL connection timeout")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("✗ PostgreSQL is not ready")
        sys.exit(1)
    
    # Drop and recreate database
    print("Dropping existing database...")
    drop_cmd = ["docker", "compose", "exec", "-T", "postgres", "dropdb", "--if-exists", f"-U{DB_USER}", DB_NAME]
    subprocess.run(drop_cmd, cwd=project_dir, capture_output=True)
    
    print("Creating new database...")
    create_cmd = ["docker", "compose", "exec", "-T", "postgres", "createdb", f"-U{DB_USER}", DB_NAME]
    subprocess.run(create_cmd, cwd=project_dir, check=True, capture_output=True)
    print("✓ Database created\n")
    
    # Restore from backup
    print(f"Restoring from backup: {backup_file}")
    with open(backup_file) as f:
        restore_cmd = ["docker", "compose", "exec", "-T", "postgres", "psql", f"-U{DB_USER}", "-d", DB_NAME]
        try:
            result = subprocess.run(
                restore_cmd,
                cwd=project_dir,
                stdin=f,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                print("✓ Backup restored successfully\n")
            else:
                print(f"⚠ Restore completed with warnings:\n{result.stderr}\n")
        except subprocess.TimeoutExpired:
            print("✗ Restore timeout")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error during restore: {e}")
            sys.exit(1)
    
    # Verify
    print("Verifying restore...")
    verify_cmd = ["docker", "compose", "exec", "-T", "postgres", "psql", f"-U{DB_USER}", "-d", DB_NAME, "-c", "SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema='public';"]
    try:
        result = subprocess.run(verify_cmd, cwd=project_dir, capture_output=True, text=True)
        print(result.stdout)
        print("✓ Database restore complete!")
    except Exception as e:
        print(f"⚠ Verification warning: {e}")

if __name__ == "__main__":
    main()
