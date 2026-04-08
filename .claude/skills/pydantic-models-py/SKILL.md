---
name: pydantic-models-py
description: Enforces Pydantic v2 model design patterns including schema definition, validators, serialization, and financial data handling. Use when creating or reviewing Pydantic models, schemas, validators, serializers, or when the user mentions request/response models, data validation, or type coercion.
license: MIT
compatibility: Designed for Claude Code. Requires Python 3.11+, Pydantic v2.
metadata:
  project: ledgerly
  stack: FastAPI, Pydantic v2, PostgreSQL, SQLAlchemy
---

# Pydantic v2 Model Best Practices

## Schema Organization
- Schemas live in `backend/app/*/schemas.py` — one file per domain module.
- Define separate schemas for Create, Update, Read, and DB representations. Example:
  - `TransactionCreate` — input for creation (no `id`, no `created_at`)
  - `TransactionResponse` — output returned to clients (computed fields OK)
  - `TransactionDB` — mirrors DB model (for internal use)

## Model Definition
- Inherit from `BaseModel` for all schemas.
- Use `model_config = ConfigDict(from_attributes=True)` on response schemas that map from ORM models.
- Always declare explicit types — never use `Any` unless absolutely unavoidable.
- Use `Optional[T]` (or `T | None`) with `default=None` for nullable/optional fields.
- Add docstrings to complex schemas.

## Financial Fields
- **NEVER use `float` for currency.** Use `Decimal` with constraints:
  ```python
  from decimal import Decimal
  from pydantic import condecimal

  amount: Annotated[Decimal, Field(gt=0, decimal_places=2, max_digits=12)]
  ```
- Ensure `Decimal` is serialized as a string in JSON responses to avoid float precision loss.

## Validators
- Use `@field_validator` for field-level validation. Use `@model_validator` for cross-field validation.
- Validators must be deterministic — same input always produces same output.
- Raise `ValueError` (not `AssertionError`) in validators — Pydantic wraps these properly.

```python
@field_validator("amount")
@classmethod
def amount_must_be_positive(cls, v: Decimal) -> Decimal:
    if v <= 0:
        raise ValueError("Amount must be positive")
    return v
```

## Enums in Schemas
- Use Python `Enum` classes for fields with fixed value sets.
- Enum values must match backend DB enum strings exactly (e.g., `TransactionCategory` values are lowercase).
- Declare enums in a shared module (`backend/app/db/models.py` or `backend/app/schemas/enums.py`) to avoid duplication.

## Serialization
- Use `model.model_dump()` in Pydantic v2 (not `.dict()`).
- Use `model.model_validate(orm_obj)` (not `.from_orm()`) in Pydantic v2.
- For partial updates, use `model.model_dump(exclude_unset=True)`.

## Ledgerly-Specific Rules
- All schemas must be defined in `backend/app/*/schemas.py` — never inline in routes.
- Enum imports must come from the canonical source (`backend/app/db/models.py`).
- Input schemas for email parsing must be strict — validate all fields aggressively since email data is external.
- Use `model_config = ConfigDict(str_strip_whitespace=True)` on input schemas to normalize whitespace from parsed emails.
