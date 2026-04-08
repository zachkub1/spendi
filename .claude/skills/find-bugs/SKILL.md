---
name: find-bugs
description: Systematically scans code for bugs, logic errors, security vulnerabilities, and correctness issues. Use when the user asks to find bugs, review code for correctness, audit a function or module, or when something is behaving unexpectedly and the root cause is unknown.
license: MIT
compatibility: Designed for Claude Code. Language-agnostic; optimized for Python + TypeScript.
metadata:
  project: ledgerly
  stack: FastAPI, SQLAlchemy, Next.js, TypeScript, PostgreSQL
---

# Find Bugs

## Process
1. **Read the code first** — never comment on code you haven't read. Use the Read tool to inspect the relevant files.
2. **Trace the control flow** — follow the execution path from entry point to exit.
3. **Check each layer**: input validation → business logic → DB interactions → output serialization.
4. **Report findings** with: file path + line number, severity (critical/high/medium/low), description, and a concrete fix.

## Categories to Check

### Logic Errors
- Off-by-one errors in loops and slice indices
- Wrong operator (`<` vs `<=`, `and` vs `or`)
- Missing `return` statements (functions returning `None` implicitly)
- Incorrect condition ordering (less-specific check fires before more-specific)
- Mutable default arguments in Python (`def f(x=[])` — always a bug)

### Async / Concurrency
- Missing `await` on coroutines (common — produces a coroutine object instead of the result)
- Race conditions in shared state
- Improper session/connection lifecycle in async SQLAlchemy

### Data & Financial Correctness
- Use of `float` for currency (must be `Decimal`)
- Integer truncation when dividing monetary amounts
- Missing `Decimal` context for rounding precision
- Date/time timezone bugs (comparing naive and aware datetimes)
- Off-by-one in date range queries (`>` vs `>=`)

### Security
- SQL injection via string interpolation (use parameterized queries only)
- Missing auth checks — routes that access user data without verifying ownership
- Secrets or PII logged to stdout/stderr
- Unvalidated external input passed to file paths or shell commands
- JWT token not validated before trusting claims

### Error Handling
- Broad `except Exception` that swallows `HTTPException` (FastAPI pattern bug)
- Silent failures (`except: pass` or bare `except:`)
- Missing error boundaries in React components
- Unhandled promise rejections in TypeScript

### State Management (Frontend)
- Missing dependencies in `useEffect` dependency arrays
- Stale closures capturing outdated state
- Raw `fetch()` calls instead of `apiClient` (auth will silently fail)
- Enum values sent to backend that don't match backend string casing

### Idempotency & Duplication
- Missing unique constraints allowing duplicate record creation
- Sync cursors advanced before confirming successful processing
- Skipping retry for failed records in idempotency checks

## Ledgerly Error Log Cross-Reference
Before reporting bugs, check `CLAUDE.md` error log for known recurring patterns:
- Gmail `From` header raw vs parsed (`email.utils.parseaddr`)
- Parser subject patterns missing email subtypes (payment, refund, alert)
- Regex ordering bugs (less-specific pattern firing before more-specific)
- `last_sync_at` advanced on partial failure
- `credentials: "include"` vs `Authorization: Bearer` auth
