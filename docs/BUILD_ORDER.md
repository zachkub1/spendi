# Implementation Roadmap: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Engineering

---

## Overview

This document provides a step-by-step implementation roadmap for building Spendi MVP. The project is divided into 5 major phases, each with clear deliverables, testing requirements, and security checkpoints.

**Total Timeline**: 12-15 weeks (3-4 months)

**Team Size**: 1-2 engineers (can be solo with AI assistance)

---

## Table of Contents

1. [Phase 0: Project Setup](#phase-0-project-setup)
2. [Phase 1: Auth + Gmail Ingestion](#phase-1-auth--gmail-ingestion)
3. [Phase 2: Transaction Normalization](#phase-2-transaction-normalization)
4. [Phase 3: Reconciliation Logic](#phase-3-reconciliation-logic)
5. [Phase 4: Rewards Engine](#phase-4-rewards-engine)
6. [Phase 5: UI & Polish](#phase-5-ui--polish)
7. [Testing Strategy](#testing-strategy)
8. [Security Checkpoints](#security-checkpoints)
9. [What to Build Manually vs AI-Generated](#what-to-build-manually-vs-ai-generated)
10. [Launch Checklist](#launch-checklist)

---

## Phase 0: Project Setup

**Duration**: 1 week

**Goal**: Set up development environment, tooling, and foundational architecture

### Deliverables

**Backend Setup**:
- [ ] Initialize FastAPI project structure
- [ ] Set up PostgreSQL database (local + Docker)
- [ ] Configure Alembic for migrations
- [ ] Set up Redis (for Celery)
- [ ] Create `.env.example` with required secrets
- [ ] Set up linting (Black, isort, flake8)
- [ ] Configure pytest with fixtures

**Frontend Setup**:
- [ ] Initialize Next.js 14 project (App Router)
- [ ] Set up Tailwind CSS + shadcn/ui
- [ ] Configure ESLint + Prettier
- [ ] Set up environment variables (`.env.local.example`)
- [ ] Create basic layout components (`<AppShell>`, `<NavBar>`)

**Infrastructure**:
- [ ] Create `docker-compose.yml` (Postgres, Redis, backend, frontend)
- [ ] Set up GitHub repository
- [ ] Configure CI/CD (GitHub Actions for tests)
- [ ] Create `.gitignore` for secrets

**Documentation**:
- [ ] Initialize `README.md` with setup instructions
- [ ] Create `CONTRIBUTING.md` (if open source)
- [ ] Set up project board (GitHub Projects or Jira)

### Success Criteria

- ✅ `docker-compose up` starts all services
- ✅ Backend serves "Hello World" at `http://localhost:8000`
- ✅ Frontend renders at `http://localhost:3000`
- ✅ Tests run with `pytest` (backend) and `npm test` (frontend)

---

## Phase 1: Auth + Gmail Ingestion

**Duration**: 3 weeks

**Goal**: Users can log in with Google OAuth and connect Gmail for transaction ingestion

### Week 1: OAuth Authentication

**Deliverables**:
- [ ] Google OAuth client setup (console.cloud.google.com)
- [ ] Backend: OAuth routes (`/auth/google/authorize`, `/auth/google/callback`)
- [ ] Backend: Session token generation (JWT with HS256)
- [ ] Backend: User model + CRUD
- [ ] Frontend: Login page with "Sign in with Google" button
- [ ] Frontend: Auth middleware (check session token)
- [ ] Frontend: User menu (logout, profile)

**Testing**:
- [ ] Unit test: JWT generation and verification
- [ ] Integration test: OAuth callback flow (mock Google API)
- [ ] Manual test: End-to-end OAuth login

**Security Checkpoint**:
- [ ] Session tokens use `httpOnly`, `Secure`, `SameSite=Lax` cookies
- [ ] OAuth client secret stored in environment variable (not hardcoded)
- [ ] HTTPS enforced in production

### Week 2: Gmail API Integration

**Deliverables**:
- [ ] OAuth scope for Gmail (`gmail.readonly`)
- [ ] Backend: Gmail OAuth routes (`/auth/google/authorize-gmail`, `/auth/google/gmail-callback`)
- [ ] Backend: EmailAccount model with encrypted OAuth tokens
- [ ] Backend: Envelope encryption module (AWS KMS or local for dev)
- [ ] Backend: Gmail API client wrapper
- [ ] Frontend: Email connection page (connect/disconnect Gmail)
- [ ] Frontend: Sync status indicator

**Testing**:
- [ ] Unit test: Token encryption/decryption
- [ ] Integration test: Gmail API message fetching (mock API)
- [ ] Manual test: Connect Gmail and fetch 10 test emails

**Security Checkpoint**:
- [ ] OAuth tokens encrypted at rest (envelope encryption)
- [ ] Tokens never logged or exposed in error messages
- [ ] Gmail API uses minimal scopes (`readonly` only)

### Week 3: Email Parsing Pipeline

**Deliverables**:
- [ ] Backend: RawEmail model
- [ ] Backend: Email discovery job (query Gmail API with sender filters)
- [ ] Backend: Email parser registry (Chase, Amex, Venmo, Zelle)
- [ ] Backend: ParsedTransaction model
- [ ] Backend: Celery task for email sync
- [ ] Backend: Scheduler (daily sync at 2 AM)
- [ ] Frontend: Sync button (trigger manual sync)

**Testing**:
- [ ] Unit test: Each email parser (Chase, Amex, Venmo, Zelle)
- [ ] Integration test: Full sync pipeline (mock Gmail API)
- [ ] Test fixtures: Sample emails for each issuer

**Success Criteria**:
- ✅ User can connect Gmail via OAuth
- ✅ Daily sync job fetches new emails
- ✅ Parsers extract merchant, amount, date, card last 4
- ✅ Parsed transactions stored in database

---

## Phase 2: Transaction Normalization

**Duration**: 2 weeks

**Goal**: Parsed transactions normalized into unified ledger with payment instrument matching and categorization

### Week 4: Payment Instrument Matching

**Deliverables**:
- [ ] Backend: PaymentInstrument model (credit cards, P2P accounts)
- [ ] Backend: Payment instrument CRUD API
- [ ] Backend: Matching logic (by last 4 digits or account identifier)
- [ ] Backend: NormalizedTransaction model
- [ ] Backend: Normalization pipeline (ParsedTransaction → NormalizedTransaction)
- [ ] Frontend: Add card page (manual entry)
- [ ] Frontend: Card list page

**Testing**:
- [ ] Unit test: Payment instrument matching (by last 4)
- [ ] Integration test: Normalization pipeline end-to-end

### Week 5: Category Inference & Merchant Normalization

**Deliverables**:
- [ ] Backend: Merchant normalization rules (SQ *X → Square, AMZN → Amazon)
- [ ] Backend: Category inference (Tier 1: rule-based merchant mapping)
- [ ] Backend: Category confidence scoring
- [ ] Backend: User category override API
- [ ] Frontend: Transaction list page (with categories)
- [ ] Frontend: Edit category modal

**Testing**:
- [ ] Unit test: Merchant normalization (20+ test cases)
- [ ] Unit test: Category inference (known merchants)

**Success Criteria**:
- ✅ Parsed transactions matched to payment instruments
- ✅ Transactions normalized with clean merchant names
- ✅ Categories auto-assigned (rule-based, 80%+ accuracy)
- ✅ Users can override categories manually

---

## Phase 3: Reconciliation Logic

**Duration**: 2 weeks

**Goal**: Reimbursement linking with automatic matching and side-by-side view

### Week 6: Reimbursement Data Model & Manual Linking

**Deliverables**:
- [ ] Backend: ReimbursementLink model (many-to-one)
- [ ] Backend: Database trigger (update reimbursed_amount)
- [ ] Backend: Link reimbursement API (`POST /reconciliation/reimbursements/{id}/link`)
- [ ] Backend: Expected reimbursement API
- [ ] Frontend: Link reimbursement modal (select unlinked transfer)
- [ ] Frontend: Add expected reimbursement modal

**Testing**:
- [ ] Unit test: Reimbursement link creation
- [ ] Unit test: Trigger updates reimbursed_amount correctly
- [ ] Integration test: Link reimbursement end-to-end

### Week 7: Automatic Matching Algorithm

**Deliverables**:
- [ ] Backend: Three-pass matching algorithm (exact amount, merchant match, proximity)
- [ ] Backend: Confidence scoring (0-100)
- [ ] Backend: Auto-linking logic (confidence ≥ 85)
- [ ] Backend: Suggested matches API (`GET /reconciliation/reimbursements/{id}/matches`)
- [ ] Frontend: Suggested matches UI (show top 3 suggestions)
- [ ] Frontend: Transaction detail page (side-by-side reimbursement view)

**Testing**:
- [ ] Unit test: Each matching pass (exact, merchant, proximity)
- [ ] Integration test: Auto-matching with various scenarios
- [ ] Edge case tests: Over-reimbursement warning, duplicate detection

**Success Criteria**:
- ✅ Users can manually link reimbursements to purchases
- ✅ System auto-suggests matches (85%+ confidence)
- ✅ Transaction detail page shows side-by-side view (Purchase | Reimbursements | Net)
- ✅ Multiple reimbursements per purchase supported

---

## Phase 4: Rewards Engine

**Duration**: 2 weeks

**Goal**: Calculate credit card rewards per transaction with time-bound promotions

### Week 8: Rewards Profiles & Calculation

**Deliverables**:
- [ ] Backend: RewardsProfile model (category_rates JSONB)
- [ ] Backend: PointsTransaction model (immutable)
- [ ] Backend: Rewards calculation engine
- [ ] Backend: Rule hierarchy (manual override > promotion > standard)
- [ ] Backend: Rewards calculation trigger (after normalization)
- [ ] Frontend: Add card rewards form (rates by category)
- [ ] Frontend: Card detail page (rewards summary)

**Testing**:
- [ ] Unit test: Rewards calculation (points per dollar, cashback percent)
- [ ] Unit test: Rule hierarchy (manual > promotion > standard)
- [ ] Integration test: Rewards calculated for new transaction

### Week 9: Time-Bound Promotions & Manual Overrides

**Deliverables**:
- [ ] Backend: Time-bound promotion support (valid_from/valid_until)
- [ ] Backend: PointsOverride model
- [ ] Backend: Recalculate rewards API (`POST /rewards/transactions/{id}/recalculate`)
- [ ] Frontend: Promotion badge (Q1 2026: 5% groceries 🔥)
- [ ] Frontend: Edit category (triggers rewards recalculation)
- [ ] Frontend: Rewards summary dashboard

**Testing**:
- [ ] Unit test: Time-bound promotion selection (Q1 vs Q2 rates)
- [ ] Integration test: Manual category override triggers recalculation

**Success Criteria**:
- ✅ Rewards calculated for every credit card transaction
- ✅ Time-bound promotions supported (Discover rotating 5%)
- ✅ Users can override category (rewards recalculated)
- ✅ Reimbursements do NOT claw back points

---

## Phase 5: UI & Polish

**Duration**: 3 weeks

**Goal**: Complete all UI pages, polish interactions, mobile optimization

### Week 10-11: Core Pages

**Deliverables**:
- [ ] Frontend: Dashboard page (net spend, recent transactions, pending reimbursements, rewards)
- [ ] Frontend: Transactions ledger (list view, filters, search, infinite scroll)
- [ ] Frontend: Transaction detail view (side-by-side, explainer tooltips)
- [ ] Frontend: Cards & rewards page (card list, reward structure)
- [ ] Frontend: Email connections page (sync status, connect/disconnect)
- [ ] Frontend: Settings page (profile, privacy, export, delete account)

**Testing**:
- [ ] E2E tests: Playwright/Cypress for critical flows
  - Login → Connect Gmail → View transactions
  - Link reimbursement manually
  - Override category → See rewards recalculated

### Week 12: Mobile Optimization & Accessibility

**Deliverables**:
- [ ] Frontend: Mobile-responsive layouts (320px - 767px)
- [ ] Frontend: Touch targets (44×44px minimum)
- [ ] Frontend: Keyboard navigation (Tab, Enter)
- [ ] Frontend: Screen reader ARIA labels
- [ ] Frontend: Dark mode toggle
- [ ] Frontend: Loading states (skeletons, spinners)
- [ ] Frontend: Error states (empty states, error messages)

**Testing**:
- [ ] Manual test: Mobile devices (iPhone, Android)
- [ ] Accessibility audit: Lighthouse (aim for 95+ score)
- [ ] Screen reader test: VoiceOver (Mac) or NVDA (Windows)

**Success Criteria**:
- ✅ All 6 pages implemented and responsive
- ✅ Mobile-first design (works on 320px screens)
- ✅ WCAG 2.1 Level AA compliance
- ✅ Dark mode works across all pages

---

## Testing Strategy

### Unit Tests (Backend)

**What to Test**:
- Email parsers (Chase, Amex, Venmo, Zelle)
- Merchant normalization logic
- Category inference
- Reimbursement matching algorithm
- Rewards calculation engine
- Token encryption/decryption

**Tools**: pytest, pytest-cov

**Coverage Target**: 80%+ (critical paths: 100%)

**Example**:
```python
def test_chase_parser():
    parser = ChaseParser()
    email = "Your Chase card ending in 5678 was used for a $12.50 transaction at BLUE BOTTLE on 02/10/2026."
    result = parser.parse(email)
    assert result['amount'] == Decimal('12.50')
    assert result['merchant_raw'] == 'BLUE BOTTLE'
    assert result['payment_instrument_hint'] == '5678'
```

---

### Integration Tests (Backend)

**What to Test**:
- OAuth callback flow (mock Google API)
- Email sync pipeline (mock Gmail API)
- Normalization pipeline (ParsedTransaction → NormalizedTransaction)
- Reconciliation flow (link reimbursement)
- Rewards calculation (after category change)

**Tools**: pytest, pytest-mock, httpx (for API mocking)

**Example**:
```python
def test_email_sync_pipeline(db_session, mock_gmail_api):
    # Mock Gmail API response
    mock_gmail_api.users().messages().list.return_value.execute.return_value = {
        'messages': [{'id': 'msg-001'}]
    }

    # Run sync
    sync_email_account(email_account_id)

    # Assertions
    raw_emails = db_session.query(RawEmail).all()
    assert len(raw_emails) == 1
    assert raw_emails[0].parsing_status == 'success'
```

---

### End-to-End Tests (Frontend)

**What to Test**:
- User login flow (OAuth)
- Connect Gmail flow
- View transactions list
- Link reimbursement manually
- Override category (rewards recalculated)
- Export data
- Delete account

**Tools**: Playwright or Cypress

**Example**:
```javascript
test('User can link reimbursement to purchase', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.click('text=Sign in with Google');
  // ... OAuth flow ...

  // Go to transaction detail
  await page.goto('/transactions/txn-001');

  // Click link reimbursement
  await page.click('text=Link Reimbursement');

  // Select unlinked transfer
  await page.click('text=Venmo from Sarah');

  // Confirm
  await page.click('text=Link');

  // Verify net amount updated
  await expect(page.locator('text=Net Cost: $0.00')).toBeVisible();
});
```

---

### Manual Testing Checklist

**Before Each Release**:
- [ ] Test OAuth login (Google)
- [ ] Test Gmail connection (connect, disconnect)
- [ ] Test email sync (manual trigger)
- [ ] Test transaction list (filters, search)
- [ ] Test reimbursement linking (manual, auto-suggest)
- [ ] Test category override (rewards recalculated)
- [ ] Test data export (JSON, CSV)
- [ ] Test account deletion (soft delete, 30-day grace)
- [ ] Test mobile layout (iPhone, Android)
- [ ] Test dark mode toggle
- [ ] Test accessibility (keyboard nav, screen reader)

---

## Security Checkpoints

### Checkpoint 1: After Phase 1 (Auth + Gmail)

**Review**:
- [ ] OAuth tokens encrypted at rest (envelope encryption)
- [ ] Session tokens use secure cookies (`httpOnly`, `Secure`, `SameSite=Lax`)
- [ ] HTTPS enforced in production
- [ ] No credentials in logs or error messages
- [ ] Rate limiting on OAuth endpoints (prevent brute force)

**Penetration Test**: Try to access another user's data (should fail)

---

### Checkpoint 2: After Phase 3 (Reconciliation)

**Review**:
- [ ] User can only access their own transactions (DB-level checks)
- [ ] API endpoints validate user ownership before returning data
- [ ] SQL injection prevented (parameterized queries via SQLAlchemy)
- [ ] XSS prevented (React escapes by default, but verify)
- [ ] CSRF protection (SameSite cookies)

**Penetration Test**: Try to link reimbursement to another user's transaction (should fail)

---

### Checkpoint 3: Before Launch (Phase 5)

**Review**:
- [ ] All API endpoints require authentication
- [ ] Data export only returns current user's data
- [ ] Account deletion fully removes data (soft delete + 30-day purge)
- [ ] Privacy policy published (plain English)
- [ ] No dark patterns (easy to delete account, clear data usage)
- [ ] Dependency scan (Snyk/Dependabot for vulnerabilities)
- [ ] Content Security Policy (CSP) header configured
- [ ] HSTS header configured (`Strict-Transport-Security`)

**External Audit**: Consider hiring security firm for penetration test (if budget allows)

---

## What to Build Manually vs AI-Generated

### ✅ AI-Safe (Claude Can Generate)

**Backend**:
- [ ] Boilerplate code (models, CRUD endpoints)
- [ ] Email parsers (regex patterns)
- [ ] Merchant normalization rules
- [ ] Unit tests (based on specifications)
- [ ] API documentation (OpenAPI specs)

**Frontend**:
- [ ] Component scaffolding (basic structure)
- [ ] Layout components (AppShell, NavBar)
- [ ] Form components (inputs, buttons)
- [ ] Utility functions (date formatting, currency)

**Prompt Example**:
```
Create a FastAPI endpoint that returns all transactions for the current user,
filtered by date range, card, and category. Include pagination (50 per page).
Use SQLAlchemy for DB queries. Add unit tests with pytest.
```

---

### ⚠️ AI-Assisted (Review Required)

**Backend**:
- [ ] OAuth flows (review token handling)
- [ ] Encryption logic (review key management)
- [ ] Complex business logic (reconciliation, rewards)
- [ ] Database migrations (review schema changes)

**Frontend**:
- [ ] State management (review data flow)
- [ ] Complex interactions (multi-step modals)
- [ ] Performance optimizations (review caching)

**Workflow**:
1. Generate code with AI
2. **Review carefully** (line-by-line)
3. Test thoroughly (unit + integration)
4. Refactor if needed

---

### 🚫 Manual Only (Human Must Write)

**Security-Critical**:
- [ ] OAuth client secret configuration (manual env var setup)
- [ ] Production encryption key generation (manual, store in KMS)
- [ ] Database connection strings (manual, secure storage)
- [ ] SSL certificate installation (manual, Let's Encrypt)

**Product Decisions**:
- [ ] UX flows (human judgment required)
- [ ] Edge case handling (requires domain knowledge)
- [ ] Error messaging (user-facing, requires empathy)

**Deployment**:
- [ ] Production deployment (manual first time, then automate)
- [ ] Database backups (manual setup, then schedule)
- [ ] Monitoring & alerts (manual setup: Sentry, Datadog)

---

## Launch Checklist

### Pre-Launch (1 Week Before)

**Backend**:
- [ ] All tests passing (unit, integration)
- [ ] Test coverage ≥ 80%
- [ ] No security vulnerabilities (dependency scan)
- [ ] Database migrations tested (on staging)
- [ ] Background jobs tested (email sync runs daily)
- [ ] API rate limiting configured
- [ ] Logging configured (structured JSON logs)

**Frontend**:
- [ ] All pages implemented
- [ ] Mobile responsive (tested on real devices)
- [ ] Accessibility audit passed (Lighthouse 95+)
- [ ] Dark mode works
- [ ] Loading states implemented
- [ ] Error states implemented (empty, error messages)

**Infrastructure**:
- [ ] Production database provisioned (PostgreSQL)
- [ ] Redis provisioned (for Celery)
- [ ] SSL certificate installed (HTTPS)
- [ ] Environment variables configured (secrets in KMS)
- [ ] Backup strategy configured (daily automated backups)
- [ ] Monitoring configured (Sentry for errors, Datadog for metrics)

**Legal**:
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Cookie banner (if EU users)

---

### Launch Day

**Steps**:
1. Deploy backend to production (blue-green deployment)
2. Run database migrations (`alembic upgrade head`)
3. Deploy frontend to production (Vercel/Netlify)
4. Smoke test: Login, connect Gmail, sync transactions
5. Monitor logs for errors (Sentry dashboard)
6. Monitor metrics (API response time, error rate)
7. Announce launch (Product Hunt, social media)

---

### Post-Launch (1 Week After)

**Monitoring**:
- [ ] Check error rate (aim for <1%)
- [ ] Check API response time (aim for <500ms p95)
- [ ] Check user onboarding funnel (% who connect Gmail)
- [ ] Check transaction parsing accuracy (% parsed successfully)

**User Feedback**:
- [ ] Send survey to beta users (NPS score)
- [ ] Monitor support requests (common issues?)
- [ ] Prioritize bug fixes and feature requests

**Iterate**:
- [ ] Fix critical bugs (within 24 hours)
- [ ] Address top user complaints (within 1 week)
- [ ] Plan V2 features (based on feedback)

---

## Milestone Summary

| Phase | Duration | Key Deliverable | Success Metric |
|-------|----------|-----------------|----------------|
| **0: Setup** | 1 week | Dev environment ready | `docker-compose up` works |
| **1: Auth + Gmail** | 3 weeks | Users can log in and connect Gmail | 90%+ emails parsed successfully |
| **2: Normalization** | 2 weeks | Transactions normalized with categories | 80%+ categories auto-detected correctly |
| **3: Reconciliation** | 2 weeks | Reimbursements linked to purchases | 85%+ auto-match confidence |
| **4: Rewards** | 2 weeks | Rewards calculated per transaction | 100% of credit card transactions have points |
| **5: UI & Polish** | 3 weeks | All pages implemented and responsive | Lighthouse score 95+ |
| **Launch** | 1 week | MVP live in production | 100 beta users signed up |

**Total**: 12-15 weeks (3-4 months)

---

## Recommended Development Order (Day-by-Day)

### Week 1: Project Setup + Auth Foundation

**Day 1-2**: Backend setup
- Initialize FastAPI project
- Set up PostgreSQL + Alembic
- Create User model + CRUD

**Day 3-4**: OAuth backend
- Google OAuth client setup
- OAuth routes (`/authorize`, `/callback`)
- JWT session tokens

**Day 5**: Frontend setup
- Initialize Next.js project
- Create login page
- "Sign in with Google" button

---

### Week 2-3: Gmail Integration

**Day 6-8**: Gmail OAuth
- Gmail OAuth routes
- EmailAccount model
- Token encryption (envelope)

**Day 9-10**: Gmail API client
- Gmail API wrapper
- Fetch messages
- Query with sender filters

**Day 11-15**: Email parsing
- RawEmail model
- ParsedTransaction model
- Parsers (Chase, Amex, Venmo, Zelle)
- Celery task for sync

---

### Week 4-5: Transaction Normalization

**Day 16-18**: Payment instruments
- PaymentInstrument model
- Matching logic (by last 4)
- Add card page (frontend)

**Day 19-22**: Normalization pipeline
- NormalizedTransaction model
- Merchant normalization
- Category inference
- Transaction list page (frontend)

---

### Week 6-7: Reconciliation

**Day 23-25**: Reimbursement data model
- ReimbursementLink model
- Database trigger
- Link reimbursement API

**Day 26-30**: Auto-matching
- Three-pass matching algorithm
- Suggested matches API
- Transaction detail page (frontend)

---

### Week 8-9: Rewards

**Day 31-33**: Rewards calculation
- RewardsProfile model
- PointsTransaction model
- Calculation engine

**Day 34-37**: Promotions & overrides
- Time-bound promotions
- PointsOverride model
- Card detail page (frontend)

---

### Week 10-12: UI & Polish

**Day 38-45**: All pages
- Dashboard
- Transactions ledger
- Cards & rewards
- Email connections
- Settings

**Day 46-50**: Polish
- Mobile responsive
- Dark mode
- Accessibility
- Error states

**Day 51-55**: Testing & deployment
- E2E tests
- Security review
- Deploy to production

---

## Document History

| Version | Date       | Author      | Changes                           |
|---------|------------|-------------|-----------------------------------|
| 1.0     | 2026-02-11 | Engineering | Initial implementation roadmap    |

---

**Questions? Contact**: engineering@spendi.app