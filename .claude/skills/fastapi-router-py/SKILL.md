---
name: fastapi-router-py
description: Enforces FastAPI router design patterns including route organization, dependency injection, response models, error handling, and middleware. Use when creating or reviewing FastAPI routes, APIRouter, dependencies, path operations, or when the user mentions FastAPI endpoints, request validation, or HTTP error responses.
license: MIT
compatibility: Designed for Claude Code. Requires Python 3.11+, FastAPI 0.100+.
metadata:
  project: ledgerly
  stack: FastAPI, SQLAlchemy, Pydantic v2, PostgreSQL
---

# FastAPI Router Best Practices

## Route Organization
- Routes live in `backend/app/*/routes.py`. Business logic goes in `backend/app/*/services.py`. DB access goes in `backend/app/*/repositories.py`.
- Use `APIRouter` with a `prefix` and `tags` for every domain module.
- Register routers in `main.py` via `app.include_router()`.

## Path Operations
- Use the correct HTTP methods: `GET` for reads, `POST` for creates, `PUT/PATCH` for updates, `DELETE` for deletes.
- Always declare a `response_model` on every route — it controls what gets serialized.
- Declare path parameters with type hints (FastAPI validates and converts automatically).
- Use `status.HTTP_201_CREATED` for resource creation responses.

## Request & Response Models
- All request bodies and response bodies must be Pydantic models (defined in `schemas/`).
- Use `response_model_exclude_unset=True` when partial updates are involved.
- Never return ORM model instances directly — always map to a Pydantic schema.

## Dependency Injection
- Use `Depends()` for: DB sessions, auth verification, pagination params, permission checks.
- DB sessions must come from `Depends(get_db)` and be closed automatically via the generator pattern.
- Auth requires a valid JWT — use the `get_current_user` dependency on all protected routes.
- Never access `request.state` for auth — always use typed dependencies.

## Error Handling
- Raise `HTTPException` with appropriate status codes for client errors.
- NEVER wrap an entire route handler in `except Exception` — it swallows `HTTPException`.
- Pattern: `except HTTPException: raise` BEFORE any broad `except Exception` handler.
- Use structured `HTTPException` detail dicts for machine-readable errors.

```python
# Correct pattern
async def my_route(...):
    try:
        result = service.do_thing()
    except HTTPException:
        raise  # never swallow intentional HTTP errors
    except SomeDomainError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

## Security
- All routes (except `/auth/*` and `/health`) must require `get_current_user` dependency.
- Always verify that the authenticated user owns the resource before returning or modifying it.
- Use parameterized queries only — SQLAlchemy ORM handles this; never use raw string interpolation.
- Never log PII (emails, tokens, financial data) — log IDs and operation names only.

## Validation
- Validate all external input at the route layer via Pydantic.
- Enum query parameters must match the exact string values of the backend enum.
- Use `Field(gt=0)`, `Field(max_length=...)` etc. to add constraints in schemas.

## Ledgerly-Specific Rules
- Business logic goes in `services/`, not in routes — routes are HTTP + validation only.
- Never use `float` for financial amounts — use `Decimal` with `condecimal(max_digits=12, decimal_places=2)`.
- Every DB mutation must be idempotent-safe and use proper transactions.
