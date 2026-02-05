# Agent Notes

**Project Structure**: Monorepo with 3 applications

- `/backend` - Python Litestar API (port 8000)
- `/frontend` - Astro SSR caregiver portal (port 4321)
- `/admin_portal` - React/Vite admin portal (port 3002 in dev, or 5173 default)

**Important**: Run all tests from a nix-shell to ensure Playwright/system dependencies are available.

---

## 🚨 CRITICAL: Testing & Code Quality Requirements

**ALWAYS run the following for impacted code after making changes:**

### Backend (Python)
```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"

# 1. Run tests
uv run pytest tests/ -v --tb=short

# 2. Type checking (ty/pyright)
uv run ty check app

# 3. Linting
uv run ruff check .

# 4. Formatting
uv run ruff format .
```

### Frontend (Astro)
```bash
cd frontend

# 1. Run E2E tests (requires backend running)
nix-shell --run "pnpm run test:e2e"

# 2. Linting
pnpm run lint

# 3. Formatting
pnpm run format
```

### Admin Portal (React/Vite)
```bash
cd admin_portal

# 1. Run E2E tests (requires backend running)
nix-shell --run "pnpm run test"

# 2. Linting - formatter disabled, uses Prettier only
pnpm exec biome lint

# 3. Format check
pnpm run format:check

# 4. Formatting  
pnpm run format
```

**Rule**: After ANY code change, run tests + type check + lint + format for the impacted service(s).

**Before pushing**: Run `act --job <job-name> -W .github/workflows/ci.yml` to test CI locally.

---

## Backend API

The backend is a Python REST API built using Litestar, SQLAlchemy, and PostgreSQL, located in `/backend`.

**Default Port**: 8000  
**Tech Stack**: Litestar, SQLAlchemy, Advanced-Alchemy, PostgreSQL, Redis (worker queue)  
**Authentication**:

- Magic link tokens (caregiver portal)
- OAuth 2.0 Google (admin portal)
- Admin email allowlist validation

### Backend Structure

```
backend/
├── app/
│   ├── server/           # Server config, ASGI app, middleware
│   │   ├── asgi.py       # App factory
│   │   ├── config.py     # Settings
│   │   ├── security.py   # Rate limiting, audit logging
│   ├── domains/          # Domain-driven design
│   │   ├── admin/        # Admin endpoints (/api/v1/admin/*)
│   │   │   ├── controllers/  # REST endpoints
│   │   │   ├── services/     # Business logic
│   │   │   ├── schemas/      # Pydantic models
│   │   │   └── guards.py     # Authorization
│   │   ├── caregiver/    # Caregiver endpoints (/api/v1/caregiver/*)
│   │   │   ├── controllers/
│   │   │   ├── services/
│   │   │   ├── schemas/
│   │   │   └── guards.py
│   ├── db/
│   │   ├── models.py     # SQLAlchemy ORM models
│   │   └── migrations/   # Alembic migrations
│   ├── lib/              # Shared utilities
│   └── worker/           # Background tasks (ARQ)
├── tests/                # Pytest tests
├── pyproject.toml        # Dependencies (uv)
└── entrypoint.sh         # Docker entrypoint
```

### Backend Development

**Start development server** (with auto-reload):

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar run --reload --host 0.0.0.0 --port 8000
```

**Run in background** (for testing frontend):

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar run --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

**Check backend is running**:

```bash
curl http://localhost:8000/api/v1/health
```

**View logs**:

```bash
tail -f /tmp/backend.log
```

**Stop background server**:

```bash
pkill -f "litestar run"
```

### Database Migrations

**Create migration**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar database make-migrations -m "description"
```

**Run migrations**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar database upgrade --no-prompt
```

**Rollback migration**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar database downgrade --no-prompt
```

### Backend Testing

**Run all tests with coverage**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest --cov=app
```

**Run specific test file**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest tests/test_security.py -v
```

**Run tests matching pattern**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest -k "test_admin" -v
```

### Backend Linting

**Format code**:

```bash
cd backend
uv run ruff format .
```

**Check linting issues**:

```bash
cd backend
uv run ruff check .
```

**Fix auto-fixable issues**:

```bash
cd backend
uv run ruff check . --fix
```

**Type checking**:

```bash
cd backend
uv run ty check app
```

## Frontend (Caregiver Portal)

The caregiver portal is built with Astro SSR and located in `/frontend`.

**Default Port**: 4321  
**Tech Stack**: Astro, TypeScript, TailwindCSS, Playwright (E2E tests)  
**Authentication**: Magic link token (email-based)

### Frontend Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   ├── layouts/         # Page layouts
│   ├── pages/           # Astro pages (file-based routing)
│   │   ├── index.astro          # Home/landing
│   │   ├── login.astro          # Magic link login
│   │   ├── dashboard.astro      # Caregiver dashboard
│   │   ├── sessions/            # Session browsing
│   │   ├── children/            # Manage children
│   │   └── account/             # Account settings
│   ├── lib/             # Utilities, API clients
│   └── styles/          # Global styles
├── tests/
│   └── e2e/             # Playwright E2E tests
├── public/              # Static assets
├── astro.config.mjs     # Astro configuration
├── playwright.config.ts # Playwright configuration
└── package.json         # pnpm dependencies
```

### Frontend Development

**Install dependencies**:

```bash
cd frontend
pnpm install
```

**Start development server**:

```bash
cd frontend
pnpm run dev
# Opens at http://localhost:4321
```

**Build for production**:

```bash
cd frontend
pnpm run build
```

**Preview production build**:

```bash
cd frontend
pnpm run preview
```

### Frontend Testing

**Run E2E tests** (requires backend running):

```bash
# From project root with nix-shell
cd /home/leon/Projects/sessions
nix-shell --run "cd frontend && pnpm run test:e2e"
```

**Run E2E tests in UI mode**:

```bash
cd frontend
nix-shell --run "pnpm run test:ui"
```

**Run E2E tests in headed mode** (see browser):

```bash
cd frontend
nix-shell --run "pnpm run test:headed"
```

**Run specific test file**:

```bash
cd frontend
nix-shell --run "pnpm exec playwright test tests/e2e/auth.spec.ts"
```

**Test Results**: 42 E2E tests covering:

- Authentication (magic link)
- Dashboard
- Session browsing and signup
- Children management (CRUD, edit)
- Account settings

### Frontend Linting

**Run Biome linter**:

```bash
cd frontend
pnpm run lint
```

**Fix linting issues**:

```bash
cd frontend
pnpm run lint:fix
```

**Format code**:

```bash
cd frontend
pnpm run format
```

---

## Admin Portal

The admin portal is a React SPA built with Vite, located in `/admin_portal`.

**Default Port**: 5173 (Vite default), or 3002 if 3001 is taken  
**Tech Stack**: React 19, TypeScript, Vite, TailwindCSS, Axios, React Router, Playwright  
**Authentication**: OAuth 2.0 Google with admin email allowlist

### Admin Portal Structure

```
admin_portal/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Alert.tsx           # Loading, error messages
│   │   ├── Layout.tsx          # Page layout wrapper
│   │   ├── Sidebar.tsx         # Navigation menu
│   │   ├── Modal.tsx           # Generic modal
│   │   ├── ProtectedRoute.tsx  # Auth guard
│   │   ├── ErrorBoundary.tsx   # Error handling
│   │   ├── FormComponents.tsx  # Form inputs
│   │   ├── FormFields.tsx      # Complex form fields
│   │   ├── CalendarView.tsx    # Calendar component
│   │   └── BulkEmailModal.tsx  # Email composition
│   ├── pages/            # Page components
│   │   ├── Login.tsx           # OAuth Google login
│   │   ├── Dashboard.tsx       # Stats, recent sessions
│   │   ├── Sessions.tsx        # Session list, CRUD
│   │   ├── SessionDetail.tsx   # View session, occurrences
│   │   ├── CreateSession.tsx   # Create session form
│   │   ├── EditSession.tsx     # Edit session form
│   │   ├── SessionCalendar.tsx # Calendar view
│   │   ├── Locations.tsx       # Location CRUD
│   │   ├── LocationDetail.tsx  # Location details
│   │   ├── Staff.tsx           # Staff CRUD
│   │   ├── StaffCalendar.tsx   # Staff schedule
│   │   ├── Students.tsx        # Student list
│   │   ├── Child.tsx           # Student details
│   │   ├── Terms.tsx           # Term CRUD
│   │   ├── Blocks.tsx          # Block CRUD
│   │   ├── Exclusions.tsx      # Exclusion CRUD
│   │   └── AttendanceRoll.tsx  # Mark attendance
│   ├── services/
│   │   └── api.ts        # Axios API client (40+ endpoints)
│   ├── context/
│   │   └── AuthContext.tsx     # Auth state management
│   ├── types/            # TypeScript interfaces
│   ├── lib/              # Utilities
│   └── config.ts         # App configuration
├── tests/
│   └── e2e/              # Playwright E2E tests (6 files)
│       ├── auth.spec.ts
│       ├── dashboard.spec.ts
│       ├── sessions.spec.ts
│       ├── locations-terms.spec.ts
│       ├── api.spec.ts
│       ├── attendance.spec.ts
│       └── helpers.ts    # Test utilities
├── public/               # Static assets
├── index.html            # HTML entry point
├── vite.config.ts        # Vite configuration
├── playwright.config.ts  # Playwright configuration
└── package.json          # pnpm dependencies
```

### Admin Portal Development

**Install dependencies**:

```bash
cd admin_portal
pnpm install
```

**Start development server**:

```bash
cd admin_portal
pnpm run dev
# Opens at http://localhost:5173 (or 3002 if port conflicts)
```

**Build for production**:

```bash
cd admin_portal
pnpm run build
```

**Preview production build**:

```bash
cd admin_portal
pnpm run preview
```

### Admin Portal Testing

**Run E2E tests** (requires backend running):

```bash
# From project root with nix-shell
cd /home/leon/Projects/sessions
nix-shell --run "cd admin_portal && pnpm run test"
```

**Run E2E tests in UI mode**:

```bash
cd admin_portal
nix-shell --run "pnpm run test:ui"
```

**Run E2E tests in headed mode**:

```bash
cd admin_portal
nix-shell --run "pnpm run test:headed"
```

**Run specific test file**:

```bash
cd admin_portal
nix-shell --run "pnpm exec playwright test tests/e2e/auth.spec.ts"
```

### Admin Portal Linting

**Run Biome linter**:

```bash
cd admin_portal
pnpm run lint
```

**Fix linting issues**:

```bash
cd admin_portal
pnpm run lint:fix
```

**Format code**:

```bash
cd admin_portal
pnpm run format
```

### Admin Portal Pages (17 total)

**Current Implementation**:

- ✅ Login (OAuth Google)
- ✅ Dashboard (stats, recent sessions)
- ✅ Sessions (list, search, filter, CRUD)
- ✅ Session Detail (occurrences, signups)
- ✅ Create/Edit Session
- ✅ Session Calendar
- ✅ Locations (CRUD)
- ✅ Location Detail
- ✅ Staff (CRUD, assignments)
- ✅ Staff Calendar
- ✅ Students (list, search)
- ✅ Child Detail
- ✅ Terms (CRUD)
- ✅ Blocks (CRUD)
- ✅ Exclusions (CRUD)
- ✅ Attendance Roll

**Missing Pages** (see ADMIN_PORTAL_FUNCTIONALITY_REPORT.md):

- ❌ Caregivers (parent management) - CRITICAL
- ⚠️ Signups (global view) - HIGH PRIORITY

---

## Docker & Docker Compose

**Start all services**:

```bash
docker compose up -d
```

**View logs**:

```bash
docker compose logs -f
```

**Stop all services**:

```bash
docker compose down
```

**Rebuild and restart**:

```bash
docker compose up --build -d
```

**Services**:

- `backend` - API on port 8000
- `frontend` - Caregiver portal on port 4321
- `admin_portal` - Admin portal on port 3002
- `postgres` - PostgreSQL database on port 5432
- `redis` - Redis (worker queue) on port 6379

---

## Quick Reference

### Start Full Development Environment

**Terminal 1 - Backend**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run litestar run --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend**:

```bash
cd frontend
pnpm run dev
```

**Terminal 3 - Admin Portal**:

```bash
cd admin_portal
pnpm run dev
```

**Access**:

- Backend API: <http://localhost:8000>
- Caregiver Portal: <http://localhost:4321>
- Admin Portal: <http://localhost:5173> (or 3002)
- API Docs: <http://localhost:8000/docs/schema.yaml> (OpenAPI)

### Run All Tests

**Backend**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest --cov=app
```

**Frontend E2E** (requires backend running):

```bash
nix-shell --run "cd frontend && pnpm run test:e2e"
```

**Admin Portal E2E** (requires backend running):

```bash
nix-shell --run "cd admin_portal && pnpm run test"
```

### Common Issues

**Port conflicts**: Check ports with `ss -tlnp | grep <port>`  
**Backend not running**: `curl http://localhost:8000/api/v1/health`  
**Playwright timeout**: Run tests from nix-shell for dependencies  
**Database connection**: Ensure PostgreSQL is running (Docker or local)  

### Security Testing

**Test admin allowlist**:

```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest tests/test_security.py -v
```

**Test rate limiting**:

```bash
# Make rapid requests to magic-link endpoint
for i in {1..10}; do curl -X POST http://localhost:8000/api/v1/caregiver/auth/magic-link -H "Content-Type: application/json" -d '{"email":"test@example.com"}'; done
```

### Database Access

**Connect to PostgreSQL** (Docker):

```bash
docker compose exec postgres psql -U postgres -d sessions
```

**View tables**:

```sql
\dt
```

**View schema**:

```sql
\d+ tablename
```

---

## 🚀 CI/CD Pipeline

The project uses GitHub Actions for continuous integration. All jobs are defined in `.github/workflows/ci.yml`.

### CI Jobs Overview

The CI pipeline runs 11+ jobs across 3 main stages:

#### **Stage 1: Linting & Type Checking**
- `backend-lint` - Ruff linting & type checking with Pyright
- `frontend-lint` - Biome linter & Prettier format check
- `admin-portal-lint` - Biome linter & Prettier format check

#### **Stage 2: Build Verification**
- `backend-build` - Python build validation
- `frontend-build` - Astro build (pages + site)
- `admin-portal-build` - React/Vite build

#### **Stage 3: Database & Testing**
- `backend-migrations` - Database migration checks
- `backend-tests` - Pytest (356+ tests)
- `frontend-e2e` - Playwright E2E tests (42+ tests)
- `admin-portal-e2e` - Playwright E2E tests (30+ tests)

### Running CI Locally with act

Use `act` to test GitHub Actions workflows locally before pushing:

```bash
# Test specific job
act --job backend-lint -W .github/workflows/ci.yml

# Test all jobs (long-running)
act -W .github/workflows/ci.yml

# List available jobs (if supported)
act -l -W .github/workflows/ci.yml
```

**Common act jobs to verify**:
```bash
# Core linting
act --job backend-lint -W .github/workflows/ci.yml
act --job frontend-lint -W .github/workflows/ci.yml
act --job admin-portal-lint -W .github/workflows/ci.yml

# Build verification
act --job backend-build -W .github/workflows/ci.yml
act --job frontend-build -W .github/workflows/ci.yml
act --job admin-portal-build -W .github/workflows/ci.yml

# Database/tests
act --job backend-migrations -W .github/workflows/ci.yml
act --job backend-tests -W .github/workflows/ci.yml
```

### CI Requirements Checklist

Before pushing, ensure:

✅ **Backend**:
- All tests pass: `uv run pytest tests/ -v`
- Type checking passes: `uv run ty check app`
- Linting passes: `uv run ruff check .`
- Formatting: `uv run ruff format .`
- Database migrations valid

✅ **Frontend**:
- Build succeeds: `pnpm run build`
- E2E tests pass: `nix-shell --run "pnpm run test:e2e"`
- Linting passes: `pnpm run lint`
- Formatting: `pnpm run format`

✅ **Admin Portal**:
- Build succeeds: `pnpm run build`
- E2E tests pass: `nix-shell --run "pnpm run test"`
- Linting passes: `pnpm exec biome lint` (no formatter errors)
- Formatting: `pnpm run format:check`

### Linting & Formatting Configuration

#### Backend (Ruff)
- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type checker**: `pyright` (via `ty check`)
- **Config**: `backend/pyproject.toml`

#### Frontend (Biome + Prettier)
- **Formatter**: `prettier` (handles all formatting)
- **Linter**: `biome lint` (disabled formatter to avoid conflicts)
- **Config**: `frontend/biome.json`, `.prettierrc`
- **Note**: Biome lints only, Prettier formats

#### Admin Portal (Biome + Prettier)
- **Formatter**: `prettier` (handles all formatting)
- **Linter**: `biome lint` (formatter disabled)
- **Config**: `admin_portal/biome.json`, `.prettierrc`
- **Key setting**: `formatter.enabled: false` in biome.json

### Backend Test Coverage

**Current test results**: 356+ tests, all passing

Run tests with coverage:
```bash
cd backend
export LITESTAR_APP="app.server.asgi:create_app"
uv run pytest --cov=app --cov-report=html
```

View HTML coverage report:
```bash
open htmlcov/index.html
```

### Frontend E2E Test Suite

**Location**: `frontend/tests/e2e/`

**Test files** (42+ tests):
- `auth.spec.ts` - Authentication & magic link
- `caregiver-messaging.spec.ts` - Messaging system
- `dashboard.spec.ts` - Dashboard page
- `sessions.spec.ts` - Session browsing & signup

Run with different modes:
```bash
# Headless (default)
nix-shell --run "cd frontend && pnpm run test:e2e"

# Interactive UI
nix-shell --run "pnpm run test:ui"

# Headed (see browser)
nix-shell --run "pnpm run test:headed"

# Debug single test
nix-shell --run "pnpm exec playwright test tests/e2e/auth.spec.ts --debug"
```

### Admin Portal E2E Test Suite

**Location**: `admin_portal/tests/e2e/`

**Test files** (30+ tests):
- `auth.spec.ts` - OAuth login & session handling
- `dashboard.spec.ts` - Admin dashboard
- `sessions.spec.ts` - Session CRUD operations
- `locations-terms.spec.ts` - Locations & terms management
- `staff-assignment.spec.ts` - Staff assignments
- `staff-calendar.spec.ts` - Staff calendar view
- `api.spec.ts` - API endpoint tests
- `attendance.spec.ts` - Attendance roll marking
- `helpers.ts` - Test utilities & JWT token generation

**Key test helper**:
```bash
# In helpers.ts: createAdminSessionToken()
# Generates real JWT tokens matching backend's admin_session_cookie
# NO API MOCKING - all requests go to real backend
```

Run tests:
```bash
# Headless
nix-shell --run "cd admin_portal && pnpm run test"

# UI mode
nix-shell --run "pnpm run test:ui"

# Headed (see browser)
nix-shell --run "pnpm run test:headed"

# Single file
nix-shell --run "pnpm exec playwright test tests/e2e/auth.spec.ts"
```

### Troubleshooting CI Failures

**Linting fails locally but passes CI**: Formatter mismatch - run `pnpm run format` or `uv run ruff format .`

**Tests timeout on Playwright**: Ensure running from nix-shell: `nix-shell --run "cd path && pnpm run test"`

**Type checking fails**: Run `uv run ty check app` (backend) to see detailed errors

**Build fails**: Check for unused imports or TypeScript errors before pushing

**Database migration issues**: Ensure no migrations are pending: `uv run litestar database upgrade --no-prompt`

### Performance Monitoring

**Backend response time**:
```bash
curl -w '\nTotal: %{time_total}s\n' http://localhost:8000/api/v1/health
```

**Frontend build time** (should be < 5s):
```bash
cd frontend
time pnpm run build
```

**Admin portal build time** (should be < 3s):
```bash
cd admin_portal
time pnpm run build
```

### Deployment Checklist

Before deploying to production:

- [ ] All CI jobs pass
- [ ] Database migrations reviewed and tested
- [ ] Environment variables configured
- [ ] Security audit: check auth guards and input validation
- [ ] Rate limiting tested: `cd backend && uv run pytest tests/test_security.py -v`
- [ ] E2E tests pass on both frontend and admin portal
- [ ] No console errors in browser DevTools
- [ ] API documentation updated if endpoints changed
