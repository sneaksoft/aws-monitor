# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWS Monitor is a full-stack platform for managing AWS resources across multiple accounts. It consists of a Python/FastAPI backend, React/TypeScript frontend, and Terraform infrastructure.

## Commands

### Backend (from `/backend` directory)

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest                                    # Run all tests
pytest --cov=app --cov-report=term-missing  # With coverage
pytest tests/unit/test_auth.py -v         # Single test file
pytest -k "test_create_user" -v           # Run tests matching pattern

# Linting & Formatting
ruff check app tests                      # Lint
black app tests                           # Format
mypy app --ignore-missing-imports         # Type check

# Database migrations
alembic upgrade head                      # Apply migrations
alembic revision --autogenerate -m "msg"  # Create migration
```

### Frontend (from `/frontend` directory)

```bash
# Development
npm run dev                               # Vite dev server on :5173

# Tests
npm run test                              # Run tests (watch mode)
npm run test -- --run                     # Run tests once (CI mode)
npm run test:coverage                     # With coverage

# Linting & Type Checking
npm run lint                              # ESLint
npx tsc --noEmit                          # TypeScript check

# Build
npm run build                             # Production build
```

### Full Stack (from root)

```bash
docker-compose up                         # Start all services
docker-compose up -d                      # Detached mode
docker-compose down -v                    # Stop and remove volumes
```

## Architecture

```
/backend          Python FastAPI API server
/frontend         React TypeScript SPA
/terraform        AWS infrastructure (modular)
```

### Backend Structure

- **Entry point**: `app/main.py` - FastAPI app initialization and route mounting
- **Config**: `app/config.py` - Pydantic BaseSettings loading from environment
- **Database**: `app/database.py` - Async SQLAlchemy with asyncpg (PostgreSQL)
- **API routes**: `app/api/routes/` - Modular route handlers (auth, resources, cost, audit, accounts)
- **Services**: `app/services/` - Business logic layer
  - `app/services/aws/` - AWS service integrations using aioboto3 (async)
  - `app/services/auth.py` - JWT + Cognito authentication
  - `app/services/safety.py` - Safety checks before destructive operations
- **Models**: `app/models/` - SQLAlchemy ORM models and Pydantic schemas

### Frontend Structure

- **Entry point**: `src/main.tsx` → `src/App.tsx` (React Router)
- **State management**: Zustand stores in `src/store/` (auth + UI slices)
- **Data fetching**: TanStack Query with services in `src/services/`
- **Pages**: `src/pages/` - Dashboard, Inventory, Costs, Recommendations, Audit, Settings
- **API client**: `src/services/api.ts` - Axios instance with interceptors

### Key Patterns

- **Async everywhere**: Backend uses async/await for all I/O (database, AWS, Redis)
- **Dependency injection**: FastAPI's `Depends()` for database sessions and auth
- **Service layer**: AWS integrations abstracted behind service classes in `app/services/aws/`
- **Type safety**: Strict TypeScript on frontend, Pydantic + mypy on backend

### Infrastructure

- **Database**: PostgreSQL 16 (async via asyncpg)
- **Cache**: Redis 7 (session and data caching)
- **Auth**: AWS Cognito (user pool + JWT validation)
- **Deployment**: Docker → ECR → ECS (Fargate)
- **Terraform modules**: vpc, security-groups, rds, redis, ecs, cognito, iam

## Environment Configuration

Backend uses Pydantic BaseSettings. Copy `.env.example` to `.env` in both `/backend` and `/frontend`.

Key backend environment variables:
- `DATABASE_URL` - PostgreSQL connection (async format: `postgresql+asyncpg://...`)
- `REDIS_URL` - Redis connection
- `AWS_REGION`, `AWS_ROLE_ARN` - AWS assume-role configuration
- `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID` - Auth configuration

Frontend uses `VITE_` prefixed variables (e.g., `VITE_API_URL`).

## Testing

Backend tests use pytest with moto for AWS mocking. Test database uses a separate PostgreSQL instance.

Frontend tests use Vitest with React Testing Library patterns.

Both have CI coverage requirements via GitHub Actions (`.github/workflows/ci.yml`).
