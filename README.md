# Spendi

Smart Personal Finance Tracker

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose

## Quick Start

### 1. Start Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL and Redis.

### 2. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Backend will be available at http://localhost:8000

Health check: http://localhost:8000/health

### 3. Start Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend will be available at http://localhost:3000

## Project Structure

```
meMoney/
├── backend/          # FastAPI application
├── frontend/         # Next.js application
├── shared/           # Shared types and utilities
├── scripts/          # Utility scripts
├── infra/            # Infrastructure configurations
└── docs/             # Technical documentation
```

## Documentation

See [docs/](docs/) for detailed technical specifications:

- [PRD.md](docs/PRD.md) - Product Requirements
- [DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) - Core domain entities
- [AUTH_SECURITY.md](docs/AUTH_SECURITY.md) - Authentication & security
- [EMAIL_INGESTION.md](docs/EMAIL_INGESTION.md) - Email processing pipeline
- [RECONCILIATION.md](docs/RECONCILIATION.md) - Transaction matching
- [REWARDS_ENGINE.md](docs/REWARDS_ENGINE.md) - Credit card rewards
- [UI_UX.md](docs/UI_UX.md) - User interface design
- [BUILD_ORDER.md](docs/BUILD_ORDER.md) - Implementation roadmap