---
name: postgres-best-practices
description: Enforces PostgreSQL schema design, query optimization, indexing, and data integrity patterns. Use when designing migrations, writing queries, reviewing SQLAlchemy models, adding indexes, or when the user mentions database performance, constraints, transactions, or schema changes.
license: MIT
compatibility: Designed for Claude Code. Requires PostgreSQL 16, SQLAlchemy 2.x.
metadata:
  project: ledgerly
  stack: PostgreSQL 16, SQLAlchemy 2.x, Alembic, Python
---

# PostgreSQL Best Practices

## Schema Design
- Every table must have a primary key (prefer `UUID` or `BIGSERIAL`).
- Financial amounts must use `NUMERIC(12, 2)` — never `FLOAT` or `REAL`.
- Use `TIMESTAMPTZ` for all timestamps (timezone-aware). Never use `TIMESTAMP` without TZ.
- Add `NOT NULL` constraints wherever nullability is not semantically meaningful.
- Add `DEFAULT now()` on `created_at`; update `updated_at` via trigger or application.

## Constraints & Integrity
- Use `UNIQUE` constraints for natural keys (e.g., `message_id` on `raw_emails`).
- Use foreign keys with `ON DELETE` behavior explicitly set (`CASCADE`, `RESTRICT`, or `SET NULL`).
- Use `CHECK` constraints for domain validation (e.g., `amount > 0`).
- Every `UNIQUE` constraint implies an index — don't add a redundant explicit index.

## Indexing
- Add indexes on every foreign key column (PostgreSQL does not do this automatically).
- Add indexes on columns used in `WHERE`, `ORDER BY`, or `JOIN` clauses in frequent queries.
- Use partial indexes for filtered queries (e.g., `WHERE status = 'pending'`).
- Use `EXPLAIN ANALYZE` to verify index usage before shipping.

## Queries & SQLAlchemy
- Use SQLAlchemy ORM or Core — never raw string SQL unless absolutely necessary.
- Avoid N+1 queries: use `joinedload()` or `selectinload()` for related data.
- Paginate all list endpoints with `LIMIT` + `OFFSET` or keyset pagination.
- Wrap multi-step mutations in explicit transactions (`async with session.begin()`).
- Use `session.execute(select(...))` in SQLAlchemy 2.x style (not legacy `session.query()`).

## Migrations (Alembic)
- Every schema change must have a reversible migration (`upgrade` + `downgrade`).
- Never modify existing migrations — always create a new one.
- Test migrations against a real PostgreSQL instance before merging.
- Add `server_default` in migrations for new NOT NULL columns on existing tables.

## Performance
- Use `RETURNING` clause to avoid extra `SELECT` after `INSERT/UPDATE`.
- Batch inserts with `insert().values([...])` — never loop with individual inserts.
- Use connection pooling (SQLAlchemy `AsyncEngine` with `pool_size`, `max_overflow`).
- Monitor slow queries in logs: `log_min_duration_statement = 200` (ms).

## Ledgerly-Specific Rules
- Append-only principle: **never** `UPDATE` or `DELETE` transaction records. Mark as voided/superseded.
- `RawEmail.message_id` must be UNIQUE — enforce at DB level, not just application level.
- `ParsedTransaction.raw_email_id` and `NormalizedTransaction.parsed_transaction_id` must be UNIQUE (1:1 relationships).
- Never store tokens, passwords, or PII in plain text — use encrypted columns or reference secrets manager.
