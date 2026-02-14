# AWS Monitor

A full-stack platform for managing and monitoring AWS resources across multiple accounts. Built with FastAPI, React, and Terraform.

## Features

- **Multi-Account Management** — Monitor resources across multiple AWS accounts from a single dashboard
- **Resource Inventory** — View and manage EC2 instances, RDS databases, S3 buckets, Lambda functions, and ECS services
- **Cost Analysis** — Track spending with breakdowns and optimization recommendations via AWS Cost Explorer
- **Audit Logging** — Comprehensive logging of all user actions, failed operations, and admin overrides with export support
- **Protected Resources** — Configurable tag-based protection requiring admin override codes for production resources
- **Authentication** — AWS Cognito integration with JWT validation

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, aioboto3 |
| **Frontend** | React 18, TypeScript, TanStack Query, Zustand, Tailwind CSS, Vite |
| **Database** | PostgreSQL 16 (asyncpg), Redis 7 |
| **Infrastructure** | Terraform, AWS ECS (Fargate), ALB, RDS, ElastiCache, Cognito |
| **CI/CD** | GitHub Actions, Docker, ECR |

## Project Structure

```
aws-monitor/
├── backend/                    # FastAPI API server
│   ├── app/
│   │   ├── main.py            # Entry point and route mounting
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # Async SQLAlchemy setup
│   │   ├── api/routes/        # API endpoints
│   │   ├── services/aws/      # AWS service integrations
│   │   └── models/            # ORM models and schemas
│   ├── alembic/               # Database migrations
│   └── tests/                 # pytest test suite
├── frontend/                   # React/TypeScript SPA
│   ├── src/
│   │   ├── pages/             # Dashboard, Inventory, Costs, Recommendations, Audit, Settings
│   │   ├── components/        # Reusable UI components
│   │   ├── services/          # API client (Axios)
│   │   └── store/             # Zustand state management
├── terraform/                  # AWS infrastructure (modular)
│   └── modules/               # vpc, rds, redis, ecs, ecr, iam, cognito, cloudfront
├── .github/workflows/         # CI and deploy pipelines
├── docker-compose.yml         # Development environment
└── docker-compose.prod.yml    # Production environment
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)
- AWS account with appropriate permissions (for deployment)

### Quick Start (Docker)

1. **Clone the repository:**

   ```bash
   git clone https://github.com/sneaksoft/aws-monitor.git
   cd aws-monitor
   ```

2. **Set up environment variables:**

   ```bash
   cp backend/.env.example backend/.env
   ```

   Edit `backend/.env` with your configuration. For local development, the defaults work with the Docker Compose services.

3. **Start all services:**

   ```bash
   docker-compose up
   ```

   This starts PostgreSQL, Redis, the backend API (port 8000), and the frontend dev server (port 5173).

4. **Open the app:** http://localhost:5173

### Local Development

#### Backend

```bash
cd backend
pip install -r requirements.txt

# Apply database migrations
alembic upgrade head

# Start the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/production) | `development` |
| `DATABASE_URL` | PostgreSQL connection string (async format) | — |
| `REDIS_URL` | Redis connection string | — |
| `CACHE_TTL` | Cache TTL in seconds | `300` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `AWS_ROLE_ARN` | Cross-account assume-role ARN | — |
| `COGNITO_USER_POOL_ID` | AWS Cognito user pool ID | — |
| `COGNITO_CLIENT_ID` | Cognito client ID | — |
| `ADMIN_OVERRIDE_CODE` | Override code for protected resources | — |
| `PROTECTED_TAGS` | Comma-separated tags requiring override | `production,prod,critical` |
| `CORS_ORIGINS` | Allowed CORS origins | `localhost:3000,localhost:5173` |

### Frontend

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |

## API Endpoints

| Prefix | Description |
|--------|-------------|
| `GET /api/health` | Health check |
| `/api/auth` | Authentication (login, token refresh) |
| `/api/resources` | AWS resource inventory |
| `/api/actions` | Perform actions on resources (start, stop, etc.) |
| `/api/cost` | Cost analysis and recommendations |
| `/api/audit` | Audit log viewing and export |
| `/api/accounts` | AWS account management |

## Testing

### Backend

```bash
cd backend
pytest                                      # Run all tests
pytest --cov=app --cov-report=term-missing  # With coverage
pytest tests/unit/test_auth.py -v           # Single file
pytest -k "test_create_user" -v             # Pattern match
```

### Frontend

```bash
cd frontend
npm run test                # Watch mode
npm run test -- --run       # Single run (CI)
npm run test:coverage       # With coverage
```

### Linting & Type Checking

```bash
# Backend
cd backend
ruff check app tests                    # Lint
black app tests                         # Format
mypy app --ignore-missing-imports       # Type check

# Frontend
cd frontend
npm run lint                            # ESLint
npx tsc --noEmit                        # TypeScript check
```

## Deployment

### Infrastructure (Terraform)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your configuration

terraform init
terraform plan
terraform apply
```

This provisions a complete AWS environment: VPC, RDS, ElastiCache, ECS Fargate cluster, ALB, Cognito user pool, ECR repositories, and IAM roles.

### CI/CD

The project uses GitHub Actions for continuous integration and deployment:

- **CI** (`.github/workflows/ci.yml`) — Runs on all PRs: backend tests, frontend tests, linting, type checking, Docker build validation, and Terraform format check
- **Deploy** (`.github/workflows/deploy.yml`) — Builds Docker images, pushes to ECR, and deploys to ECS Fargate

## License

This project is proprietary software. All rights reserved.
