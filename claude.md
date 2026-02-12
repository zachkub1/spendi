# Ledgerly - Smart Personal Finance Tracker

## Overview

Ledgerly is a privacy-first personal finance tracker that automatically ingests financial data from email (transaction receipts, statements, rewards notifications), reconciles transactions across accounts, and provides explainable insights into spending patterns and optimization opportunities.

**Core Value Proposition:**
- Automated transaction ingestion from email (Gmail API)
- Multi-account reconciliation with conflict resolution
- Rewards optimization and tracking
- Explainable finance: every calculation, categorization, and insight is auditable
- Privacy-first: your data stays yours

## Design Principles

### 1. Privacy-First
- User data is never sold or shared with third parties
- All external credentials (OAuth tokens, API keys) are encrypted at rest
- Minimal data retention: only what's necessary for functionality
- Users can export or delete their data at any time
- Local-first processing where possible (client-side calculations for non-sensitive operations)

### 2. Explainable Finance
- Every transaction categorization includes reasoning
- Budget recommendations show the underlying data and logic
- Spending insights link back to specific transactions
- Rewards calculations are transparent and verifiable
- No "black box" ML models without interpretability

### 3. Correctness & Auditability
- All transaction logic is unit tested
- Reconciliation conflicts are surfaced to users, not silently resolved
- Financial calculations use decimal precision (never float arithmetic)
- Transaction history is immutable (append-only ledger pattern)
- State changes are logged and traceable

### 4. Developer Experience
- Type-safe contracts between frontend and backend (shared types)
- Comprehensive error handling with actionable messages
- Developer-friendly logging and observability
- Clear separation of concerns across modules

## Core Constraints

### Technical Constraints
1. **No User Data Sales**: Architecture must not support bulk data export or third-party integrations that compromise privacy
2. **Encrypted Credentials**: All OAuth tokens, refresh tokens, and API keys stored using envelope encryption
3. **Auditable Transaction Logic**: Every transaction mutation logged with timestamp, user, and reason
4. **Decimal Precision**: All currency calculations use Python `Decimal` or DB `NUMERIC` types
5. **Idempotent Operations**: All transaction ingestion and reconciliation must be safely retryable

### Product Constraints
1. **Email-First Ingestion**: Use Gmail API (not raw IMAP scraping) with proper OAuth consent flow
2. **Graceful Degradation**: If email ingestion fails, users can still manually enter transactions
3. **Explainable Categorization**: ML-based categorization must output confidence scores and reasoning
4. **User Control**: Users can override any automatic categorization or reconciliation

## Tech Stack

### Backend
- **Framework**: FastAPI (async, type-safe, OpenAPI auto-documentation)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Background Jobs**: Celery with Redis broker (or APScheduler for simpler deployments)
- **Email Ingestion**: Gmail API with OAuth 2.0
- **Auth**: OAuth 2.0 (Google initially, extensible to other providers)
- **Testing**: pytest with fixtures for DB isolation

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Styling**: Tailwind CSS with shadcn/ui components
- **State Management**: React Context + Server Components where possible
- **Forms**: react-hook-form with Zod validation
- **API Client**: fetch with OpenAPI-generated types

### Infrastructure
- **Containerization**: Docker + docker-compose for local development
- **Secrets Management**: Environment variables (local), cloud KMS (production)
- **Logging**: Structured JSON logs with correlation IDs
- **Monitoring**: Application-level healthchecks and metrics endpoints

## How Claude Code Should Assist

### 1. Incremental, Safe Changes
- **Read before modifying**: Always read existing files to understand context and patterns
- **Preserve conventions**: Follow established naming, structure, and error handling patterns
- **Ask before major refactors**: If a change affects multiple modules, propose the plan first

### 2. Test-Driven Development
- **Tests first**: For critical financial logic (reconciliation, rewards calculation), write tests before implementation
- **Test coverage**: Ensure new endpoints and transaction logic have unit tests
- **Test data**: Use realistic but anonymized test fixtures

### 3. Type Safety
- **Shared types**: Backend Pydantic models should have corresponding TypeScript types in `shared/types/`
- **Validation**: Use Pydantic for backend validation, Zod for frontend validation
- **Avoid `any`**: Prefer explicit types or `unknown` with type guards

### 4. Security Mindset
- **Input validation**: Never trust user input; validate and sanitize at API boundaries
- **SQL injection**: Use parameterized queries (SQLAlchemy handles this)
- **Secrets**: Never log or expose credentials, tokens, or PII
- **Auth checks**: Verify user ownership before returning or modifying data

### 5. Documentation
- **Docstrings**: Add docstrings to non-trivial functions explaining purpose and edge cases
- **API docs**: FastAPI auto-generates OpenAPI docs; ensure endpoint descriptions are clear
- **README updates**: Update module READMEs when adding new functionality

### 6. Code Quality
- **Linting**: Follow project linting rules (Black for Python, ESLint/Prettier for TypeScript)
- **Error handling**: Use structured exceptions with context, not generic `Exception`
- **Logging**: Log at appropriate levels (DEBUG for details, INFO for key events, ERROR for failures)
- **Comments**: Explain *why*, not *what* (the code shows what it does)

## Key Workflows

### Transaction Ingestion Pipeline
1. User authorizes Gmail API access (OAuth flow)
2. Background job polls Gmail for new financial emails (daily/hourly)
3. Parser extracts transaction data (merchant, amount, date, card last 4 digits)
4. Transaction record created with `status: pending_reconciliation`
5. Reconciliation engine matches against bank-imported transactions
6. User reviews and approves matches; conflicts surfaced for manual resolution

### Reconciliation Logic
- **Match criteria**: date window (±2 days), amount exact match, merchant fuzzy match
- **Conflict handling**: If multiple matches found, flag for user review
- **Audit trail**: Log match reasoning (`matched_by: exact_amount_and_date`)

### Rewards Tracking
- **Category tracking**: Track spending by category (e.g., dining, gas, groceries)
- **Card-specific rules**: Store reward rates per card per category
- **Optimization hints**: "You spent $X on dining; Card Y offers better rewards"

## Project Structure Philosophy

- **Modular backend**: Each domain (transactions, reconciliation, rewards) is a self-contained module with its own models, routes, and tests
- **Shared types**: TypeScript types generated from Pydantic models ensure frontend/backend consistency
- **Clear boundaries**: API layer handles HTTP concerns; business logic in service modules; data access in repositories
- **Testability**: Dependencies injected (DB sessions, external API clients) for easy mocking

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis (if using Celery)

### Initial Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head

# Frontend
cd frontend
npm install
npm run dev
```

### Development Workflow
1. Start PostgreSQL and Redis
2. Run backend: `uvicorn app.main:app --reload`
3. Run Celery worker: `celery -A app.jobs.worker worker --loglevel=info`
4. Run frontend: `npm run dev`
5. Visit http://localhost:3000

## Future Enhancements
- Multi-currency support
- Investment tracking (stocks, crypto)
- Budget forecasting with ML
- Mobile app (React Native)
- Multi-user households with shared accounts