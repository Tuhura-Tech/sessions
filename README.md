# Sessions Management System

[![CI](https://github.com/Tuhura-Tech/sessions/actions/workflows/ci.yml/badge.svg)](https://github.com/Tuhura-Tech/sessions/actions/workflows/ci.yml)
[![Build and Push Docker Images](https://github.com/Tuhura-Tech/sessions/actions/workflows/publish.yml/badge.svg)](https://github.com/Tuhura-Tech/sessions/actions/workflows/publish.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

A comprehensive session management platform for organizing and managing youth programs, classes, and activities. The system provides both public-facing session discovery and caregiver signup capabilities, along with powerful administrative tools for staff.

## 🌟 Features

### Public Features

- **Session Discovery**: Browse available sessions by region with search and filtering
- **Detailed Information**: View session schedules, locations, age requirements, and capacity
- **Calendar Export**: Download session calendars in .ics format for personal calendars

### Caregiver Portal

- **Magic Link Authentication**: Secure, passwordless login via email
- **Child Management**: Register and manage multiple children
- **Session Signups**: Enroll children in sessions with automatic age eligibility checking
- **Waitlist Management**: Automatic waitlist placement when sessions are full or age-ineligible
- **Session History**: Track enrollments and attendance

### Admin Portal

- **Google OAuth Authentication**: Secure staff login with Google accounts
- **Session Management**: Create and manage term-based and special sessions
- **Block/Term Configuration**: Set up school terms and special event blocks
- **Location Management**: Configure venues with maps and details
- **Attendance Tracking**: Take attendance with detailed roll calls
- **Student Management**: View student profiles, medical info, and signup history
- **Exclusion Dates**: Manage school holidays and closure dates
- **Calendar Overview**: Visual calendar of all session occurrences
- **Bulk Communications**: Send emails to session participants

## 🏗️ Architecture

The system consists of three main components:

| Component | Tech Stack | Purpose |
|-----------|-----------|---------|
| **Backend API** | Python 3.13+, Litestar, PostgreSQL | RESTful API with business logic |
| **Admin Portal** | React 19, TypeScript, Tailwind CSS | Staff administration interface |
| **Frontend** | Astro 5, TypeScript, Tailwind CSS | Public session discovery and caregiver portal |

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Development](#-development)
- [Database Management & Migrations](#database-management--migrations)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [API Documentation](#-api-documentation)
- [Database Schema](#-database-schema)
- [Contributing](#-contributing)
- [Support](#-support)

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** - For containerized development and deployment
- **Node.js 24+** & **pnpm 10+** - For frontend/admin portal development
- **Python 3.13+** & **uv** - For backend development
- **PostgreSQL 16+** - For local development (optional if using Docker)

### Quick Setup with Docker

```bash
git clone https://github.com/Tuhura-Tech/sessions.git
cd sessions
docker compose up -d
```

Access the application:
- Frontend: http://localhost:4321
- Admin Portal: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development Setup

#### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your configuration
uv sync
uv run alembic upgrade head
uv run litestar run --reload
```

The backend will be available at `http://localhost:8000`

#### Admin Portal

```bash
cd admin_portal
cp .env.example .env
pnpm install
pnpm run dev
```

Access at `http://localhost:5173`

#### Frontend

```bash
cd frontend
pnpm install
pnpm run dev
```

Access at `http://localhost:4321`

## 🛠️ Development

### Project Structure

```
sessions/
├── backend/              # Litestar REST API
│   ├── app/             # Application code
│   ├── tests/           # Unit and integration tests
│   └── alembic/         # Database migrations
├── admin_portal/         # React admin dashboard
│   ├── src/             # React components and logic
│   └── tests/           # Playwright E2E tests
├── frontend/             # Astro public site
│   ├── src/             # Astro components and pages
│   └── tests/           # Playwright E2E tests
└── docker-compose.yml   # Local development environment
```

### Code Style & Linting

**Backend:**
```bash
cd backend
uv run ruff check .        # Lint with Ruff
uv run ruff format .       # Format with Ruff
```

**Frontend & Admin Portal:**
```bash
cd frontend  # or admin_portal
pnpm run lint:fix          # Fix with Biome
pnpm run format            # Format with Prettier
```

### Running Development Servers

All three services support hot reload:

```bash
# Terminal 1: Backend
cd backend && uv run litestar run --reload

# Terminal 2: Admin Portal
cd admin_portal && pnpm run dev

# Terminal 3: Frontend
cd frontend && pnpm run dev
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
uv run pytest                              # Run all tests
uv run pytest --cov=app --cov-report=html # With coverage report
uv run pytest -v                          # Verbose output
```

### Frontend E2E Tests

```bash
cd admin_portal
pnpm run test                     # Run Playwright tests
pnpm run test:ui                  # Interactive test UI
pnpm run test:headed              # Run with browser visible
pnpm run test:debug               # Debug mode

cd frontend
pnpm run test:e2e                 # Run E2E tests
pnpm run test:e2e:ui              # Interactive test UI
```

### Type Checking

```bash
# Frontend
cd frontend && pnpm run check

# Admin Portal
cd admin_portal && tsc --noEmit
```

## 🚢 Deployment

### Docker Images

Pre-built Docker images are automatically published to GitHub Container Registry:

```bash
ghcr.io/Tuhura-Tech/sessions/backend:latest
ghcr.io/Tuhura-Tech/sessions/admin-portal:latest
ghcr.io/Tuhura-Tech/sessions/frontend:latest
```

Images are built for both `linux/amd64` and `linux/arm64` architectures.

### Environment Variables

#### Backend

Create `backend/.env` with:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/sessions
SECRET_KEY=your-secret-key-here
LITESTAR_DEBUG=false

# OAuth
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/admin-auth/callback

# Email (optional)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
```

See `backend/.env.example` for all available options.

#### Frontend & Admin Portal

```bash
# admin_portal/.env
VITE_API_URL=http://localhost:8000/api/v1

# frontend/.env
PUBLIC_API_URL=http://localhost:8000/api/v1
```

### Database Management & Migrations

The project includes comprehensive database management scripts in the `scripts/` directory. See [scripts/README.md](scripts/README.md) for complete documentation.

#### Quick Start

```bash
# Initialize new database with sample data
python scripts/db_init.py --seed

# Reset database (development)
./scripts/db_reset.sh --seed

# Create migration
./scripts/db_migrate.sh create "Add new field"

# Apply migrations
./scripts/db_migrate.sh up
```

#### Migration Scripts

All database scripts are located in `/scripts`:

| Script | Purpose | Quick Usage |
|--------|---------|-------------|
| `db_init.py` | Initialize new database | `python scripts/db_init.py --seed` |
| `db_reset.sh` | Reset to clean state | `./scripts/db_reset.sh --seed` |
| `db_migrate.sh` | Migration management | `./scripts/db_migrate.sh up` |
| `migrate_legacy_data.py` | Import legacy data | `python scripts/migrate_legacy_data.py backup.sql` |

#### Common Workflows

**First-time setup:**
```bash
docker compose up -d
python scripts/db_init.py --seed
```

**Create & apply migration:**
```bash
./scripts/db_migrate.sh create "Add user preferences"
# Review generated file in backend/app/db/migrations/versions/
./scripts/db_migrate.sh up
```

**Reset development database:**
```bash
./scripts/db_reset.sh --seed
```

**Import legacy data:**
```bash
python scripts/migrate_legacy_data.py backup.sql
```

**Check migration status:**
```bash
./scripts/db_migrate.sh status
./scripts/db_migrate.sh history
```

#### Migration Best Practices

1. **Always use migrations for schema changes** - Never manually alter the database
2. **Test migrations both ways** - Apply and rollback to verify
3. **Review generated migrations** - Check the code in `backend/app/db/migrations/versions/`
4. **Keep migrations small** - One logical change per migration
5. **Backup before production migrations** - Always have a rollback plan

For detailed documentation, troubleshooting, and advanced usage, see **[scripts/README.md](scripts/README.md)**.

## 📚 API Documentation

The backend API is fully documented with OpenAPI/Swagger:

- **Development**: http://localhost:8000/docs
- **Production**: `https://your-domain.com/docs`

### Key Endpoints

- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions` - Create session (admin only)
- `GET /api/v1/locations` - List locations
- `POST /api/v1/signups` - Create enrollment
- `POST /api/v1/admin/login` - Admin authentication

## 🏛️ Database Schema

### Core Entities

- **Sessions** - Class/program definitions with capacity and age requirements
- **SessionBlocks** - Time periods (terms, special events)
- **SessionOccurrences** - Individual class meetings
- **Signups** - Student enrollments with status tracking
- **Students** - Student profiles with personal information
- **Caregivers** - Parent/guardian accounts
- **Staff** - Admin users with role-based access
- **Locations** - Venue information with coordinates
- **ExclusionDates** - Holidays and facility closures
- **Attendance** - Attendance records for each occurrence

### Schema Management

Migrations are managed with Alembic and tracked in `backend/app/db/migrations/versions/`.

**View current schema:**
```bash
./scripts/db_migrate.sh status
./scripts/db_migrate.sh history
```

**Modify schema:**
```bash
# 1. Update models in backend/app/db/models.py
# 2. Generate migration
./scripts/db_migrate.sh create "Describe your change"
# 3. Review migration file
# 4. Apply migration
./scripts/db_migrate.sh up
```

For complete database management documentation, see [scripts/README.md](scripts/README.md).

## 🤖 AI-Powered Development

This project uses GitHub Copilot for development assistance. See [AGENTS.md](AGENTS.md) for information about AI agents and automated development workflows.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development guidelines
- Code style standards
- PR process
- Commit message conventions

## 📄 License

This project is licensed under the [GNU Affero General Public License v3 (AGPL-3.0)](LICENSE) - see the [LICENSE](LICENSE) file for details.

## 🔒 Security

For security concerns, please email security@tuhura.co.nz instead of using the issue tracker.

See [SECURITY.md](SECURITY.md) for our full security policy and disclosure process.

## 🙏 Acknowledgments

Built with modern, industry-standard technologies:

- [Litestar](https://litestar.dev/) - Modern Python web framework
- [React](https://react.dev/) - UI library
- [Astro](https://astro.build/) - Web framework
- [PostgreSQL](https://www.postgresql.org/) - Relational database
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [Docker](https://www.docker.com/) - Container platform
- [GitHub Actions](https://github.com/features/actions) - CI/CD

## 📧 Support

For questions and support:
- Open an issue on [GitHub Issues](https://github.com/Tuhura-Tech/sessions/issues)
- Check [Discussions](https://github.com/Tuhura-Tech/sessions/discussions) for Q&A
- Email: contact@tuhuratech.org.nz

---

Made with ❤️ by the Tūhura Tech team
