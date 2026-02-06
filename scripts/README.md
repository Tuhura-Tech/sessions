# Database & Migration Scripts

This directory contains all database management, migration, and seeding scripts for the Sessions Management System.

## 📋 Quick Reference

| Script | Purpose | Usage |
|--------|---------|-------|
| `db_init.py` | Initialize new database | `python scripts/db_init.py --seed` |
| `db_migrate.sh` | Create/apply migrations | `./scripts/db_migrate.sh up` |
| `migrate_legacy_data.py` | Import legacy data | `python scripts/migrate_legacy_data.py backup.sql` |
| `migrate_backup.py` | Advanced legacy migration | `python scripts/migrate_backup.py` |
| `seed.py` | Seed minimal sample data | `python scripts/seed.py` |
| `seed_test_data.py` | Seed E2E test data | `python scripts/seed_test_data.py` |
| `setup_dev_db.sh` | One-command dev setup | `./scripts/setup_dev_db.sh` |

## 🚀 Common Workflows

### First-Time Setup

```bash
# 1. Start Docker services
docker compose up -d

# 2. Initialize database with sample data
python scripts/db_init.py --seed

# 3. Start backend
cd backend && uv run litestar run --reload
```

### Migrate Legacy Data

```bash
# From backup.sql file
python scripts/migrate_legacy_data.py backup.sql

# Dry run (preview changes without applying)
python scripts/migrate_legacy_data.py backup.sql --dry-run
```

### Create & Apply Migrations

```bash
# Create new migration
./scripts/db_migrate.sh create "Add user preferences table"

# Apply migrations
./scripts/db_migrate.sh up

# Check migration status
./scripts/db_migrate.sh status

# Rollback one migration (if needed)
./scripts/db_migrate.sh down
```

## 📖 Detailed Script Documentation

### db_init.py

**Purpose**: Initialize a fresh database with the current schema using Alembic migrations.

**Usage**:
```bash
python scripts/db_init.py [options]
```

**Options**:
- `--drop-all` - Drop all existing tables before initialization (⚠️ DANGEROUS!)
- `--seed` - Seed with sample data after initialization
- `--database-url URL` - Override DATABASE_URL from environment

**Examples**:
```bash
# Initialize new database
python scripts/db_init.py

# Initialize and seed
python scripts/db_init.py --seed

# Fresh start (destroys existing data)
python scripts/db_init.py --drop-all --seed

# Use custom database
python scripts/db_init.py --database-url postgresql://user:pass@localhost/mydb
```

**What it does**:
1. Validates database connection
2. Optionally drops all existing tables
3. Runs Alembic migrations to create schema
4. Optionally seeds sample data
5. Shows summary of database state

### db_migrate.sh

**Purpose**: Wrapper around Litestar/Alembic migration commands.

**Usage**:
```bash
./scripts/db_migrate.sh <command> [args]
```

**Commands**:

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `create` | `c`, `new` | Create new migration | `./scripts/db_migrate.sh create "Add field"` |
| `up` | `upgrade`, `apply` | Apply pending migrations | `./scripts/db_migrate.sh up` |
| `down` | `downgrade`, `rollback` | Rollback one migration | `./scripts/db_migrate.sh down` |
| `status` | `s` | Show current status | `./scripts/db_migrate.sh status` |
| `history` | `h`, `list` | Show migration history | `./scripts/db_migrate.sh history` |

**Examples**:
```bash
# Create migration
./scripts/db_migrate.sh create "Add user email verification"

# Apply all pending
./scripts/db_migrate.sh up

# Check current version
./scripts/db_migrate.sh status

# Rollback last migration
./scripts/db_migrate.sh down
```

**Migration Workflow**:
1. Create migration: `./scripts/db_migrate.sh create "description"`
2. Review generated file in `backend/app/db/migrations/versions/`
3. Edit if needed (complex changes)
4. Apply: `./scripts/db_migrate.sh up`
5. Verify: `./scripts/db_migrate.sh status`

### migrate_legacy_data.py

**Purpose**: Transform and import data from legacy backup.sql format.

**Usage**:
```bash
python scripts/migrate_legacy_data.py [backup_file] [options]
```

**Options**:
- `--dry-run` - Preview changes without applying

**Examples**:
```bash
# Import from backup.sql
python scripts/migrate_legacy_data.py backup.sql

# Preview what would be imported
python scripts/migrate_legacy_data.py backup.sql --dry-run

# Import from different file
python scripts/migrate_legacy_data.py /path/to/old_backup.sql
```

**What it does**:
1. Parses legacy SQL dump
2. Transforms table/column names
   - `children` → `students`
   - `session_locations` → `locations`
   - `child_id` → `student_id`
3. Handles schema differences
4. Validates data before insertion
5. Shows import summary

**Supported Tables**:
- sessions
- students (from children)
- caregivers
- signups
- locations (from session_locations)
- staff
- blocks (terms)
- occurrences
- exclusion_dates

### migrate_backup.py

**Purpose**: Advanced legacy migration with schema versioning.

**Usage**:
```bash
python scripts/migrate_backup.py [options]
```

**Options**:
- `--database-url URL` - Database connection string
- `--legacy-schema NAME` - Schema name for legacy tables (default: legacy)
- `--restore PATH` - Restore backup.sql before migration
- `--skip-alembic` - Skip running migrations (schema exists)

**Examples**:
```bash
# Migrate with all steps
python scripts/migrate_backup.py --restore backup.sql

# Use custom schema name
python scripts/migrate_backup.py --legacy-schema old_data --restore backup.sql

# Migration only (schema already exists)
python scripts/migrate_backup.py --skip-alembic
```

**What it does**:
1. Optionally restores backup via psql
2. Moves existing tables to legacy schema
3. Runs Alembic migrations (new schema)
4. Transforms and copies data
5. Validates data integrity

**When to use**:
- Complex migrations with schema history
- Side-by-side old/new schema comparison
- Gradual migration approach
- Debugging migration issues

### seed.py

**Purpose**: Seed database with minimal sample data.

**Usage**:
```bash
python scripts/seed.py
```

**What it seeds**:
- 1 sample location (Tūhura Tech Hub)
- 1 sample session (Beginner Coding Club)

**When to use**:
- Quick development setup
- Testing basic functionality
- Demonstrating features

**Notes**:
- Safe to run multiple times (checks for existing data)
- Minimal data for fast startup
- Use `seed_test_data.py` for comprehensive testing

### seed_test_data.py

**Purpose**: Seed comprehensive test data for E2E tests.

**Usage**:
```bash
python scripts/seed_test_data.py
```

**What it seeds**:
- 2 locations (Auckland, Wellington)
- 3 blocks/terms (Term 1, Term 2, Summer Bootcamp)
- 3 sessions with various configurations
- Session occurrences
- Block links

**When to use**:
- E2E test preparation
- Comprehensive testing scenarios
- Multiple session types needed

**Notes**:
- Cleans existing test data first
- Uses current year for dates
- Creates realistic test scenarios

### setup_dev_db.sh

**Purpose**: One-command development database setup with migrations and legacy data.

**Usage**:
```bash
./scripts/setup_dev_db.sh
```

**What it does**:
1. Runs database migrations
2. Loads legacy data from backup.sql
3. Shows row counts summary

**When to use**:
- Initial project setup with existing legacy data
- Fast database initialization
- Setting up fresh development environment

**Note**: Requires backup.sql to exist in project root. Uses migrate_legacy_data.py internally.

## 🔧 Environment Setup

### Required Environment Variables

```bash
# Required for all scripts
DATABASE_URL=postgresql+asyncpg://sessions:password@localhost:5432/sessions

# Required for migration commands
LITESTAR_APP=app.asgi:create_app
```

### .env File Locations

Scripts automatically load `DATABASE_URL` from:
1. `backend/.env` (checked first)
2. `.env` (root directory)
3. Environment variable (highest priority)

**Example backend/.env**:
```env
DATABASE_URL=postgresql+asyncpg://sessions:9e58291888...@localhost:5432/sessions
LITESTAR_APP=app.asgi:create_app
SECRET_KEY=dev-secret-key
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

## 🔍 Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check if database exists
docker compose exec postgres psql -U postgres -l

# Test connection
python -c "import psycopg; psycopg.connect('postgresql://sessions:password@localhost/sessions')"
```

### Migration Conflicts

```bash
# Check current migration state
./scripts/db_migrate.sh status

# View migration history
./scripts/db_migrate.sh history

# Manual migration check
cd backend
uv run alembic current
uv run alembic history --verbose
```

### Permission Issues

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Or run with bash explicitly
bash scripts/db_reset.sh
```

### Docker Issues

```bash
# Restart PostgreSQL container
docker compose restart postgres

# View PostgreSQL logs
docker compose logs postgres

# Recreate containers
docker compose down
docker compose up -d
```

### Legacy Data Import Fails

```bash
# Validate backup.sql format
head -20 backup.sql

# Test with dry run
python scripts/migrate_legacy_data.py backup.sql --dry-run

# Check for table mismatches
grep "CREATE TABLE" backup.sql
```

## 📝 Best Practices

### Development Workflow

1. **Always use migrations for schema changes**
   ```bash
   # Don't modify models.py and manually alter database
   # Instead:
   ./scripts/db_migrate.sh create "Add field to model"
   # Edit migration if needed
   ./scripts/db_migrate.sh up
   ```

2. **Test migrations both ways**
   ```bash
   ./scripts/db_migrate.sh up      # Apply
   ./scripts/db_migrate.sh down    # Rollback
   ./scripts/db_migrate.sh up      # Reapply
   ```

3. **Use branches for migration development**
   ```bash
   git checkout -b feature/add-user-preferences
   ./scripts/db_migrate.sh create "Add user preferences"
   # Develop & test
   git add backend/app/db/migrations/versions/*.py
   git commit -m "feat: add user preferences migration"
   ```

### Production Workflow

1. **Always backup before migrations**
   ```bash
   pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Test migrations on staging first**
   ```bash
   # On staging
   ./scripts/db_migrate.sh up
   # Run tests, verify
   ```

3. **Use downgrade for rollbacks**
   ```bash
   # If migration fails in production
   ./scripts/db_migrate.sh down
   ```

### Data Safety

- **Never use `--drop-all` in production**
- **Always confirm before running `db_reset.sh`**
- **Use `--dry-run` for legacy imports first**
- **Keep backups before major operations**

## 🧪 Testing Scripts

```bash
# Test db_init.py
python scripts/db_init.py --help

# Test db_migrate.sh
./scripts/db_migrate.sh status

# Test with Docker
docker compose up -d postgres
python scripts/db_init.py --seed
./scripts/db_migrate.sh status
```

## 📚 Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Litestar Database Guide](https://docs.litestar.dev/latest/usage/databases.html)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## 🆘 Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review script output for error messages
3. Check Docker logs: `docker compose logs`
4. Open an issue on GitHub with:
   - Script command you ran
   - Full error output
   - Your environment (OS, Python version, Docker version)
   - Database connection string (sanitized)

---

**Last Updated**: February 2026  
**Maintained by**: Tūhura Tech Team
