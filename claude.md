Spendi - Smart Personal Finance Tracker
Overview

Spendi is a privacy-first personal finance tracker that automatically ingests financial data from email (transaction receipts, statements, rewards notifications), reconciles transactions across accounts, and provides explainable insights into spending patterns and optimization opportunities.

🧠 Engineering Philosophy (CRITICAL)

This project follows high-standard software engineering discipline. Code is treated as a long-lived system, not a hackathon prototype.

Core Principles
1. DRY (Don't Repeat Yourself)
No duplicated business logic across services, routes, or jobs
Shared utilities must be abstracted into reusable modules
Repeated patterns → refactor immediately into helpers/services
Avoid copy-paste coding at all costs
2. Single Responsibility Principle (SRP)
Each function does ONE thing
Each module owns ONE domain (transactions, rewards, reconciliation)
API routes should NOT contain business logic → delegate to services
3. Separation of Concerns
API Layer → HTTP + validation
Service Layer → business logic
Repository Layer → DB interactions
Models → schema only
4. Idempotency & Determinism
All ingestion + reconciliation must be retry-safe
No duplicate transactions ever
Same input → same output (deterministic logic)
5. Explicit Over Implicit
No hidden side effects
No “magic” logic
All transformations must be traceable
🔁 Iterative Error Memory System (VERY IMPORTANT)

This project must evolve based on past mistakes.
Update docs folder respective file on requirements or bottlenecks as project evolves
Modify requirements as new requirements are presented

Rule:

Every time a bug, bad pattern, or mistake is discovered → it MUST be recorded here.

🚨 Error Log (Append-Only)
Format:
### [DATE] - [SHORT TITLE]
**Context:** What was being built
**Issue:** What went wrong
**Root Cause:** Why it happened
**Fix:** How it was resolved
**Prevention Rule:** Rule to avoid this forever
Example (keep this as template):
[2026-03-30] - Float Used for Currency

Context: Transaction calculation logic
Issue: Used Python float for money
Root Cause: Forgot precision requirements
Fix: Replaced with Decimal
Prevention Rule: NEVER use float for financial data. Only Decimal or NUMERIC.

### [2026-03-30] - Gmail From Header Format Breaks All Parser Sender Matching (100% Parse Failure)
**Context:** Email sync pipeline — `EmailSyncService.sync_email_account()` routing emails to parsers
**Issue:** 27 emails discovered, 27 failed, 0 parsed. Every email hit "No parser found for email".
**Root Cause:** `sync.py` passed the raw Gmail `From` header directly to `ParserRegistry.get_parser()`. Real Gmail `From` headers include a display name: `"Chase Alerts <no.reply.alerts@chase.com>"`. All parser `can_parse()` methods use `$`-anchored regex patterns (e.g. `@chase\.com$`). The raw header string ends with `>`, not `.com`, so every pattern returns no match. Additionally, Amex emails from `@welcome.americanexpress.com` (a subdomain) didn't match `@americanexpress\.com$` even after fixing the primary bug.
**Fix:** In `sync.py`, added `parseaddr` (stdlib `email.utils`) to extract clean email from raw `From` header before parser routing. Stored original raw header in `RawEmail.sender` for audit trail. Updated `AmexParser.SENDER_PATTERN` to handle subdomains: `@(?:[\w-]+\.)?americanexpress\.com$`. Added warning log with sender+subject when no parser matches.
**Prevention Rule:** NEVER pass raw email headers to pattern matchers. Always extract the canonical address via `email.utils.parseaddr()` first. Test sender patterns against real `From` header formats — financial institutions always use `"Display Name <email@domain.com>"`. Use subdomain-tolerant patterns (`@(?:[\w-]+\.)?domain\.com$`) for large senders.

### [2026-03-30] - Regex Pattern Ordering Causes Wrong Category
**Context:** Transaction categorization in `categorization.py`
**Issue:** "Costco Gas" categorized as GROCERIES instead of GAS; "Uber Eats" categorized as OTHER instead of DINING
**Root Cause:** (1) Dict iteration order: GROCERIES pattern `r"costco"` fires before GAS pattern `r"costco.*gas"` — less-specific patterns precede more-specific ones. (2) Delivery app pattern `r"ubereats"` has no space, but real merchant name is "Uber Eats" (with space).
**Fix:** Added negative lookahead `r"costco(?!.*gas)"` to GROCERIES; changed delivery pattern to `r"uber\s*eats"`.
**Prevention Rule:** When two categories share a keyword (e.g., Costco), put the MORE SPECIFIC pattern first OR use a negative lookahead in the less-specific one. Always test patterns against real-world merchant name variants (spaces, casing, punctuation).

### [2026-03-30] - Wrong Mock Side-Effect Count for P2P Matching Test
**Context:** Unit tests for `PaymentInstrumentMatchingService._find_matching_instrument`
**Issue:** `test_match_p2p_account_by_type` always returned `None`; `test_p2p_transfer_categorization` crashed with `AttributeError: 'NoneType'`
**Root Cause:** Mock set `side_effect = [None, p2p_instrument]` (2 calls) but code only makes 1 DB call when `card_last_four is None` (card-matching branch is guarded by `if parsed_transaction.card_last_four:`). First side-effect value `None` was consumed, returning no match.
**Fix:** Changed mock to `return_value = p2p_instrument` (single call expected for P2P-only transactions).
**Prevention Rule:** Before setting `side_effect`, trace the EXACT control flow of the function under test. Count how many times each mock method is actually called — do not assume symmetric call counts across branches.

### [2026-03-30] - Failed Emails Permanently Stuck Due to Two Interacting Bugs
**Context:** Email sync pipeline — second run after first sync resulted in 27 discovered, 27 failed
**Issue:** Second sync showed "Found 1 messages, 0 discovered, 0 parsed" — none of the 27 previously-failed emails were retried
**Root Cause:** Two bugs compounding each other: (1) `last_sync_at` was updated to the current time at the end of every sync (even when all emails failed), so the Gmail `after:` date filter excluded all previously-failed emails on the next run. (2) The idempotency check `if existing: continue` skipped ALL previously-seen emails regardless of `parsing_status`, so even if Gmail did return them, they'd be silently dropped.
**Fix:** (1) Before querying Gmail, check for `RawEmail` records with `parsing_status = "failed"` for this account; if any exist with `received_at` older than `last_sync`, extend the query window back to the oldest failure date. (2) Changed idempotency check to only skip emails with status `success` or `non_transaction`; log and retry `failed`/`pending` records by resetting their fields in-place.
**Prevention Rule:** NEVER advance a sync cursor without verifying that all items in the previous window were successfully processed. Idempotency guards must be status-aware — skipping a failed record is a silent data loss bug, not safe deduplication.

### [2026-03-30] - raw fetch() with credentials:"include" Breaks Auth Across Five Call Sites (Systemic)
**Context:** `transactions/page.tsx`, `cards/page.tsx`, `transaction-filters.tsx`, `add-instrument-modal.tsx`
**Issue:** All backend requests returned 403. Transactions showed "Failed to fetch transactions", Cards showed "Failed to fetch payment instruments". Category filter returned 422 Unprocessable Entity.
**Root Cause:** (1) Five `fetch()` calls across four files used `credentials: "include"` (cookie auth). The app uses JWT Bearer tokens in localStorage — no cookie is ever set, so the Authorization header was never sent. FastAPI's `HTTPBearer()` returns 403 (not 401) when the header is completely absent. (2) Category dropdown sent uppercase values ("SHOPPING", "GAS") but the backend `TransactionCategory` enum uses lowercase ("shopping", "gas") — FastAPI validates strictly → 422.
**Fix:** Replaced all five raw `fetch()` calls with `apiClient.get/post/delete()`. Changed CATEGORIES to lowercase to match backend enum string values exactly.
**Prevention Rule:** NEVER use raw `fetch()` for any call to the backend. `apiClient` is the ONLY approved method — it injects `Authorization: Bearer {token}` automatically. Grep for `credentials: "include"` in code review — it is always wrong in this codebase. Enum query params must exactly match backend enum string values (case-sensitive).

### [2026-03-30] - Reimbursement Status Enum Value Mismatch Between Backend and Frontend
**Context:** Transaction card reimbursement badge display in `transaction-list.tsx`
**Issue:** "Fully Reimbursed" badge never showed even for fully reimbursed transactions
**Root Cause:** Backend `ReimbursementStatus` enum defines `COMPLETE = "complete"`, but the frontend switch statement matched on `case "full"` — a value that the backend never emits.
**Fix:** Changed frontend `case "full":` to `case "complete":` to match the actual enum string value from the backend.
**Prevention Rule:** When adding enum values, define them in ONE place and share via the `@shared/types` package. Never hardcode enum string values independently in the frontend — always derive from the shared type or document the exact backend value explicitly with a comment.

### [2026-03-30] - HTTPException Swallowed by Broad Exception Handler
**Context:** `connect_gmail()` route in `email_ingest/routes.py`
**Issue:** Explicit `HTTPException(409 CONFLICT)` raised inside a try block was being caught by `except Exception as e:` and re-raised as `500 INTERNAL_SERVER_ERROR`
**Root Cause:** `HTTPException` is a subclass of `Exception`. A single broad `try/except Exception` wrapped the entire function body, including intentional HTTP error raises.
**Fix:** Added `except HTTPException: raise` before the broad handler so HTTP errors propagate unchanged.
**Prevention Rule:** NEVER wrap an entire route handler in `except Exception`. Either use narrow try/except around specific risky calls, or always add `except HTTPException: raise` as the first handler before any broad catch.

🔒 Global Prevention Rules (Auto-Enforced Mindset)
### [2026-03-30] - Parser Subject Patterns Too Narrow — Payment Emails Silently Dropped
**Context:** Discover email sync — "Your Scheduled Payment" from discover@services.discover.com
**Issue:** Subject "Your Scheduled Payment" matched no `SUBJECT_PATTERNS`, so `can_parse()` returned False, no parser was assigned, email stored as `parsing_status = "failed"`. On subsequent syncs the email was found again but (if previously stored as `non_transaction`) permanently skipped by idempotency.
**Root Cause:** (1) Parser only listed purchase-alert subjects; payment/scheduled-payment subjects were absent. (2) Idempotency check permanently skipped `non_transaction` emails even when updated patterns could now parse them. (3) Date format "March 30, 2026" (written month) unhandled — only `MM/DD/YYYY` was supported.
**Fix:** (a) Added payment subject patterns to `DiscoverParser.SUBJECT_PATTERNS`. (b) Refactored `parse()` into `_parse_payment()` / `_parse_purchase()` with `_is_payment_email()` dispatcher. (c) Added `_WRITTEN_DATE_RE` and `_PAYMENT_DATE_RE` to handle "March 30, 2026" / "Payment Post Date: March 30, 2026". (d) `sync.py` idempotency check now re-queues `non_transaction` emails when a parser reports `can_parse() = True` for the stored subject.
**Prevention Rule:** When adding a new parser, enumerate ALL email subtypes that sender produces (purchase, payment, refund, alert, statement). A parser that only handles purchases will silently drop payment notifications. Always test `can_parse()` against real subject lines from the sender before shipping. Write `_is_payment_email()` / `_is_purchase_email()` dispatch helpers to keep `parse()` readable.

NEVER use float for currency
NEVER write business logic inside API routes
NEVER silently catch exceptions (except: pass)
NEVER mutate transaction history (append-only only)
NEVER skip validation on external data (email parsing especially)
NEVER assume uniqueness without DB constraints
🏗 Design Principles
1. Privacy-First
No third-party data sharing
Encrypted credentials (OAuth tokens, API keys)
Minimal retention
User-controlled deletion/export
2. Explainable Finance
Every categorization includes reasoning
Every insight links to raw transactions
No black-box ML without explanation
3. Correctness & Auditability
Append-only ledger
All actions logged with reasoning
Full traceability of state changes
4. Developer Experience
Strong typing everywhere
Clear logs with correlation IDs
Easy-to-debug architecture
⚙️ Engineering Best Practices
Code Quality
Use meaningful names (calculate_rewards, not calc)
Avoid functions > 50 lines
Avoid nesting > 3 levels deep
Prefer early returns over deep conditionals
Error Handling
Use structured exceptions
Include:
context
user_id (if applicable)
operation being performed

Example:

raise TransactionReconciliationError(
    message="Multiple matches found",
    transaction_id=tx.id,
    candidates=len(matches)
)
Logging
DEBUG → internal details
INFO → key system events
WARNING → recoverable issues
ERROR → failures requiring attention
Testing Discipline (MANDATORY)
Rules:
All financial logic MUST have tests
Edge cases REQUIRED:
duplicate transactions
timezone issues
partial matches
malformed email input
Test Types:
Unit tests → business logic
Integration tests → DB + services
E2E (later) → ingestion pipeline
Data Integrity Rules
Use DB constraints:
unique(transaction_id)
NOT NULL where applicable
Always validate before insert
Use transactions for multi-step operations
Performance Rules
Avoid N+1 queries (use joins / eager loading)
Background jobs for heavy tasks (email parsing)
Cache only when correctness is guaranteed
🧱 Tech Stack
Backend
FastAPI
PostgreSQL
SQLAlchemy
Celery + Redis
Frontend
Next.js 14+
Tailwind + shadcn/ui
React Hook Form + Zod
🧩 Architecture Rules
Backend Structure
app/
 ├── api/           # routes only
 ├── services/      # business logic
 ├── repositories/  # DB access
 ├── models/        # ORM models
 ├── schemas/       # Pydantic models
 ├── jobs/          # background workers
 └── core/          # config, utils
Golden Rule:

If logic is reused twice → move it to services

🔐 Security Rules
Validate ALL inputs
Never expose:
tokens
emails
PII in logs
Always verify ownership before data access
Use parameterized queries ONLY
🔄 Key Workflows
Transaction Ingestion
Gmail OAuth
Poll emails
Parse transactions
Store as pending
Reconcile
User approval
Reconciliation Rules
Match:
amount EXACT
date ±2 days
merchant fuzzy match
If ambiguous → DO NOT auto-resolve
Rewards Logic
Store per-card reward rules
Always show:
how reward was calculated
which rule applied
🚀 Development Workflow
Read existing code FIRST
Check Error Log BEFORE coding
Write tests FIRST (for core logic)
Implement feature
Add logs + validation
Update Error Log if any issue found
🧠 Claude Code Instructions (STRICT)

When assisting:

ALWAYS:
Follow existing patterns
Check for DRY violations
Suggest refactors if duplication appears
Add type safety
Think about edge cases
NEVER:
Introduce silent failures
Skip validation
Write untested financial logic
Break modular boundaries
🔮 Future Enhancements
Multi-currency support
Investment tracking
ML-based forecasting (explainable)
Mobile app
✅ Final Mental Model

This system is:

A financial ledger (correctness > speed)
A developer-grade system (not a prototype)
A self-improving codebase (learns from errors)