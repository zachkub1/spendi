# Core Domain Model: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Engineering

---

## Overview

This document defines the core domain entities, relationships, and data structures for Spendi. The model is designed around three key principles:

1. **Immutability**: Transactions are append-only; modifications create new records with audit trails
2. **Explainability**: Every state change, categorization, and calculation is traceable
3. **Flexibility**: Support complex reimbursement scenarios (partial, many-to-one) and time-dependent rewards

---

## Entity Definitions

### 1. User

The primary account holder who owns all data within their scope.

**Fields:**

| Field              | Type      | Constraints                  | Description                                    |
|--------------------|-----------|------------------------------|------------------------------------------------|
| `id`               | UUID      | Primary Key                  | Unique user identifier                         |
| `email`            | String    | Unique, Not Null             | Email address (from OAuth provider)            |
| `oauth_provider`   | Enum      | Not Null                     | OAuth provider: `google`, `microsoft` (future) |
| `oauth_subject_id` | String    | Unique, Not Null             | Subject ID from OAuth provider (stable ID)     |
| `display_name`     | String    | Nullable                     | User's display name                            |
| `timezone`         | String    | Default: `UTC`               | User's preferred timezone (e.g., `America/New_York`) |
| `created_at`       | Timestamp | Not Null                     | Account creation timestamp                     |
| `updated_at`       | Timestamp | Not Null                     | Last profile update timestamp                  |
| `deleted_at`       | Timestamp | Nullable                     | Soft delete timestamp (for GDPR compliance)    |

**Relationships:**
- `User` **has many** `EmailAccount`
- `User` **has many** `PaymentInstrument`
- `User` **has many** `NormalizedTransaction`
- `User` **has many** `RewardsProfile`

**Constraints:**
- Unique index on `(oauth_provider, oauth_subject_id)`
- Soft delete: set `deleted_at` timestamp; cascade soft-delete to all related entities

**Example JSON:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "john.doe@gmail.com",
  "oauth_provider": "google",
  "oauth_subject_id": "google-oauth2|123456789",
  "display_name": "John Doe",
  "timezone": "America/Los_Angeles",
  "created_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-02-10T14:22:00Z",
  "deleted_at": null
}
```

---

### 2. EmailAccount

Represents a connected email account (Gmail initially) for transaction ingestion.

**Fields:**

| Field                   | Type      | Constraints       | Description                                           |
|-------------------------|-----------|-------------------|-------------------------------------------------------|
| `id`                    | UUID      | Primary Key       | Unique email account identifier                       |
| `user_id`               | UUID      | Foreign Key, Not Null | Reference to `User`                               |
| `provider`              | Enum      | Not Null          | Email provider: `gmail`, `outlook` (future)           |
| `email_address`         | String    | Not Null          | Email address (e.g., `john.doe@gmail.com`)            |
| `oauth_refresh_token`   | String    | Encrypted, Not Null | Encrypted OAuth refresh token                      |
| `oauth_access_token`    | String    | Encrypted, Nullable | Encrypted OAuth access token (short-lived)         |
| `oauth_token_expires_at`| Timestamp | Nullable          | Access token expiration                               |
| `sync_enabled`          | Boolean   | Default: `true`   | Whether auto-sync is enabled                          |
| `last_sync_at`          | Timestamp | Nullable          | Last successful email sync timestamp                  |
| `last_sync_status`      | Enum      | Default: `pending`| Sync status: `pending`, `success`, `failed`           |
| `created_at`            | Timestamp | Not Null          | Account connection timestamp                          |
| `updated_at`            | Timestamp | Not Null          | Last update timestamp                                 |

**Relationships:**
- `EmailAccount` **belongs to** `User`
- `EmailAccount` **has many** `RawEmail`

**Constraints:**
- Unique index on `(user_id, email_address)`
- Encryption: `oauth_refresh_token` and `oauth_access_token` encrypted at rest using envelope encryption (AES-256)

**Example JSON:**
```json
{
  "id": "7c9e6c7a-3b5f-4d2e-9f1a-8b6c5d4e3f2a",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "provider": "gmail",
  "email_address": "john.doe@gmail.com",
  "oauth_refresh_token": "ENC[aes256:...]",
  "oauth_access_token": "ENC[aes256:...]",
  "oauth_token_expires_at": "2026-02-11T18:00:00Z",
  "sync_enabled": true,
  "last_sync_at": "2026-02-11T12:00:00Z",
  "last_sync_status": "success",
  "created_at": "2026-01-15T10:35:00Z",
  "updated_at": "2026-02-11T12:00:00Z"
}
```

---

### 3. PaymentInstrument

Represents a credit card, debit card, or P2P payment account (Zelle, Venmo, Cash App).

**Fields:**

| Field               | Type      | Constraints                 | Description                                           |
|---------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                | UUID      | Primary Key                 | Unique payment instrument identifier                  |
| `user_id`           | UUID      | Foreign Key, Not Null       | Reference to `User`                                   |
| `type`              | Enum      | Not Null                    | Type: `credit_card`, `debit_card`, `p2p_account`      |
| `issuer`            | String    | Not Null                    | Issuer name: `chase`, `amex`, `citi`, `venmo`, etc.   |
| `display_name`      | String    | Not Null                    | User-friendly name (e.g., "Chase Sapphire Reserve")   |
| `last_four_digits`  | String    | Nullable                    | Last 4 digits (for cards only, e.g., "1234")          |
| `account_identifier`| String    | Nullable                    | For P2P: username/email (e.g., venmo username)        |
| `network`           | Enum      | Nullable                    | Card network: `visa`, `mastercard`, `amex`, `discover`|
| `status`            | Enum      | Default: `active`           | Status: `active`, `inactive`, `closed`                |
| `created_at`        | Timestamp | Not Null                    | Instrument creation timestamp                         |
| `updated_at`        | Timestamp | Not Null                    | Last update timestamp                                 |

**Relationships:**
- `PaymentInstrument` **belongs to** `User`
- `PaymentInstrument` **has many** `NormalizedTransaction`
- `PaymentInstrument` **has one** `RewardsProfile` (for credit cards)

**Constraints:**
- Unique index on `(user_id, type, issuer, last_four_digits)` for cards
- Unique index on `(user_id, type, issuer, account_identifier)` for P2P accounts
- `last_four_digits` required if `type` is `credit_card` or `debit_card`
- `account_identifier` required if `type` is `p2p_account`

**Example JSON (Credit Card):**
```json
{
  "id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "credit_card",
  "issuer": "chase",
  "display_name": "Chase Sapphire Reserve",
  "last_four_digits": "5678",
  "account_identifier": null,
  "network": "visa",
  "status": "active",
  "created_at": "2026-01-16T09:00:00Z",
  "updated_at": "2026-01-16T09:00:00Z"
}
```

**Example JSON (P2P Account):**
```json
{
  "id": "8e2a7b5c-4d1e-3f0a-9c8d-7e6f5a4b3c2d",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "p2p_account",
  "issuer": "venmo",
  "display_name": "Venmo (@johndoe)",
  "last_four_digits": null,
  "account_identifier": "@johndoe",
  "network": null,
  "status": "active",
  "created_at": "2026-01-17T11:30:00Z",
  "updated_at": "2026-01-17T11:30:00Z"
}
```

---

### 4. RawEmail

Stores metadata about emails received from financial institutions. **Email content is NOT stored** (privacy-first design); only extracted fields.

**Fields:**

| Field                | Type      | Constraints                 | Description                                           |
|----------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                 | UUID      | Primary Key                 | Unique email record identifier                        |
| `email_account_id`   | UUID      | Foreign Key, Not Null       | Reference to `EmailAccount`                           |
| `user_id`            | UUID      | Foreign Key, Not Null       | Reference to `User` (denormalized for query perf)     |
| `message_id`         | String    | Unique, Not Null            | Gmail message ID (for deduplication)                  |
| `sender_email`       | String    | Not Null                    | Sender email address (e.g., `alerts@chase.com`)       |
| `subject`            | String    | Not Null                    | Email subject line                                    |
| `received_at`        | Timestamp | Not Null                    | When email was received (from email headers)          |
| `synced_at`          | Timestamp | Not Null                    | When email was synced into Spendi                   |
| `parsing_status`     | Enum      | Default: `pending`          | Status: `pending`, `success`, `failed`, `skipped`     |
| `parsing_error`      | String    | Nullable                    | Error message if parsing failed                       |
| `parsed_at`          | Timestamp | Nullable                    | When email was successfully parsed                    |

**Relationships:**
- `RawEmail` **belongs to** `EmailAccount`
- `RawEmail` **belongs to** `User`
- `RawEmail` **has one** `ParsedTransaction` (if parsing succeeded)

**Constraints:**
- Unique index on `message_id` (prevents duplicate email processing)
- Index on `(user_id, received_at)` for efficient querying

**Example JSON:**
```json
{
  "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "email_account_id": "7c9e6c7a-3b5f-4d2e-9f1a-8b6c5d4e3f2a",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "gmail-msg-187a3b2c1d0e9f8g",
  "sender_email": "no-reply@chase.com",
  "subject": "Your Chase card was used",
  "received_at": "2026-02-10T14:22:30Z",
  "synced_at": "2026-02-11T12:00:15Z",
  "parsing_status": "success",
  "parsing_error": null,
  "parsed_at": "2026-02-11T12:00:18Z"
}
```

---

### 5. ParsedTransaction

Represents the raw transaction data extracted from a `RawEmail`. This is an intermediate stage before normalization.

**Fields:**

| Field                  | Type      | Constraints                 | Description                                           |
|------------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                   | UUID      | Primary Key                 | Unique parsed transaction identifier                  |
| `raw_email_id`         | UUID      | Foreign Key, Unique, Not Null | Reference to `RawEmail` (one-to-one)              |
| `user_id`              | UUID      | Foreign Key, Not Null       | Reference to `User` (denormalized)                    |
| `merchant_raw`         | String    | Not Null                    | Raw merchant string (e.g., "AMZN*abc123")             |
| `amount`               | Decimal   | Not Null                    | Transaction amount (e.g., 123.45)                     |
| `currency`             | String    | Default: `USD`              | Currency code (ISO 4217)                              |
| `transaction_date`     | Date      | Not Null                    | Transaction date (not email date)                     |
| `transaction_type`     | Enum      | Not Null                    | Type: `purchase`, `refund`, `payment`, `transfer`     |
| `payment_instrument_hint` | String | Nullable                  | Hint for matching (e.g., last 4 digits "5678")        |
| `transaction_id_external` | String | Nullable                  | External transaction ID from email (for dedup)        |
| `confidence_score`     | Integer   | Range: 0-100                | Parsing confidence (0 = low, 100 = high)              |
| `created_at`           | Timestamp | Not Null                    | Parsing timestamp                                     |

**Relationships:**
- `ParsedTransaction` **belongs to** `RawEmail` (one-to-one)
- `ParsedTransaction` **belongs to** `User`
- `ParsedTransaction` **is normalized into** `NormalizedTransaction` (one-to-one or one-to-zero if discarded)

**Constraints:**
- Unique index on `raw_email_id` (one parsed transaction per email)
- `amount` precision: `DECIMAL(12, 2)` (up to $999,999,999.99)

**Example JSON:**
```json
{
  "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
  "raw_email_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "merchant_raw": "SQ *BLUE BOTTLE COFFEE",
  "amount": 12.50,
  "currency": "USD",
  "transaction_date": "2026-02-10",
  "transaction_type": "purchase",
  "payment_instrument_hint": "5678",
  "transaction_id_external": "chase-txn-abc123xyz",
  "confidence_score": 95,
  "created_at": "2026-02-11T12:00:18Z"
}
```

---

### 6. NormalizedTransaction

The **core immutable ledger** of all transactions. Represents finalized, user-visible transactions.

**Fields:**

| Field                     | Type      | Constraints                 | Description                                           |
|---------------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                      | UUID      | Primary Key                 | Unique transaction identifier                         |
| `user_id`                 | UUID      | Foreign Key, Not Null       | Reference to `User`                                   |
| `parsed_transaction_id`   | UUID      | Foreign Key, Nullable       | Reference to `ParsedTransaction` (null if manual)     |
| `payment_instrument_id`   | UUID      | Foreign Key, Not Null       | Reference to `PaymentInstrument`                      |
| `merchant_normalized`     | String    | Not Null                    | Cleaned merchant name (e.g., "Blue Bottle Coffee")    |
| `merchant_original`       | String    | Not Null                    | Original merchant string (for reference)              |
| `amount`                  | Decimal   | Not Null                    | Transaction amount (always positive)                  |
| `currency`                | String    | Default: `USD`              | Currency code (ISO 4217)                              |
| `transaction_date`        | Date      | Not Null                    | Transaction date                                      |
| `transaction_type`        | Enum      | Not Null                    | Type: `purchase`, `refund`, `payment`, `transfer`     |
| `category`                | String    | Not Null                    | Category (e.g., "Dining", "Groceries")                |
| `category_confidence`     | Integer   | Range: 0-100, Nullable      | Auto-categorization confidence (null if user-set)     |
| `status`                  | Enum      | Default: `settled`          | Status: `pending`, `settled`, `reversed`              |
| `reimbursement_status`    | Enum      | Default: `none`             | Status: `none`, `partial`, `full`                     |
| `reimbursed_amount`       | Decimal   | Default: 0.00               | Total reimbursed amount                               |
| `net_amount`              | Decimal   | Generated                   | Computed: `amount - reimbursed_amount`                |
| `notes`                   | String    | Nullable                    | User notes                                            |
| `source`                  | Enum      | Not Null                    | Source: `email_parsed`, `manual_entry`                |
| `created_at`              | Timestamp | Not Null                    | Transaction creation timestamp                        |
| `updated_at`              | Timestamp | Not Null                    | Last update timestamp (for non-immutable fields)      |
| `version`                 | Integer   | Default: 1                  | Version number for audit trail                        |

**Immutability Rules:**
- **Immutable fields** (never change): `id`, `user_id`, `parsed_transaction_id`, `amount`, `transaction_date`, `transaction_type`, `created_at`, `source`
- **Mutable fields** (user can edit): `merchant_normalized`, `category`, `notes`, `payment_instrument_id`, `status`
- **Computed fields** (auto-updated): `reimbursed_amount`, `net_amount`, `reimbursement_status`, `updated_at`, `version`

**Version Control:**
- Each update increments `version` and logs the change in a separate `TransactionAuditLog` table
- Users can view audit history to see all changes

**Relationships:**
- `NormalizedTransaction` **belongs to** `User`
- `NormalizedTransaction` **belongs to** `PaymentInstrument`
- `NormalizedTransaction` **optionally belongs to** `ParsedTransaction`
- `NormalizedTransaction` **has many** `ReimbursementLink` (as `original_transaction_id`)
- `NormalizedTransaction` **has many** `ReimbursementLink` (as `reimbursement_transaction_id`)
- `NormalizedTransaction` **has one** `PointsTransaction` (for credit card purchases)

**Constraints:**
- Index on `(user_id, transaction_date)` for efficient date range queries
- Index on `(user_id, payment_instrument_id)` for per-card views
- `amount` precision: `DECIMAL(12, 2)`
- `reimbursed_amount` precision: `DECIMAL(12, 2)`
- Check constraint: `reimbursed_amount <= amount`
- Check constraint: `net_amount = amount - reimbursed_amount` (generated column)

**Example JSON (Purchase):**
```json
{
  "id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "parsed_transaction_id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
  "payment_instrument_id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "merchant_normalized": "Blue Bottle Coffee",
  "merchant_original": "SQ *BLUE BOTTLE COFFEE",
  "amount": 12.50,
  "currency": "USD",
  "transaction_date": "2026-02-10",
  "transaction_type": "purchase",
  "category": "Dining",
  "category_confidence": 95,
  "status": "settled",
  "reimbursement_status": "none",
  "reimbursed_amount": 0.00,
  "net_amount": 12.50,
  "notes": null,
  "source": "email_parsed",
  "created_at": "2026-02-11T12:00:20Z",
  "updated_at": "2026-02-11T12:00:20Z",
  "version": 1
}
```

**Example JSON (Manual Entry - P2P Transfer):**
```json
{
  "id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "parsed_transaction_id": null,
  "payment_instrument_id": "8e2a7b5c-4d1e-3f0a-9c8d-7e6f5a4b3c2d",
  "merchant_normalized": "Venmo - Sarah Smith",
  "merchant_original": "Venmo - Sarah Smith",
  "amount": 50.00,
  "currency": "USD",
  "transaction_date": "2026-02-09",
  "transaction_type": "transfer",
  "category": "Reimbursement",
  "category_confidence": null,
  "status": "settled",
  "reimbursement_status": "none",
  "reimbursed_amount": 0.00,
  "net_amount": 50.00,
  "notes": "Reimbursement for dinner split",
  "source": "manual_entry",
  "created_at": "2026-02-11T13:45:00Z",
  "updated_at": "2026-02-11T13:45:00Z",
  "version": 1
}
```

---

### 7. ReimbursementLink

Links reimbursement transactions (e.g., Venmo receipt) to original purchase transactions. **Immutable once created** to preserve audit trail.

**Fields:**

| Field                         | Type      | Constraints                 | Description                                           |
|-------------------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                          | UUID      | Primary Key                 | Unique reimbursement link identifier                  |
| `user_id`                     | UUID      | Foreign Key, Not Null       | Reference to `User`                                   |
| `original_transaction_id`     | UUID      | Foreign Key, Not Null       | Transaction being reimbursed                          |
| `reimbursement_transaction_id`| UUID      | Foreign Key, Nullable       | Transaction representing the reimbursement (can be null for expected reimbursements) |
| `reimbursement_amount`        | Decimal   | Not Null                    | Amount reimbursed (can be partial)                    |
| `reimbursement_source`        | String    | Not Null                    | Source description (e.g., "Work", "Friend: John")     |
| `reimbursement_date`          | Date      | Not Null                    | Date reimbursement was received (or expected)         |
| `status`                      | Enum      | Default: `confirmed`        | Status: `expected`, `confirmed`, `cancelled`          |
| `notes`                       | String    | Nullable                    | User notes                                            |
| `created_at`                  | Timestamp | Not Null                    | Link creation timestamp                               |
| `created_by`                  | Enum      | Not Null                    | Creator: `user`, `system` (auto-matched)              |

**Immutability:**
- Once a `ReimbursementLink` is created, it CANNOT be modified
- To "undo" a reimbursement, mark `status` as `cancelled` and create a new link if needed
- This preserves full audit trail of reimbursement changes

**Relationships:**
- `ReimbursementLink` **belongs to** `User`
- `ReimbursementLink` **belongs to** `NormalizedTransaction` (as `original_transaction_id`)
- `ReimbursementLink` **optionally belongs to** `NormalizedTransaction` (as `reimbursement_transaction_id`)

**Constraints:**
- Check constraint: `reimbursement_amount > 0`
- Trigger: When `ReimbursementLink` is created/updated, recompute `original_transaction.reimbursed_amount` as SUM of all linked reimbursements with `status = 'confirmed'`
- Trigger: Update `original_transaction.reimbursement_status` to `none`, `partial`, or `full` based on `reimbursed_amount` vs `amount`

**Example JSON (Full Reimbursement):**
```json
{
  "id": "5e6f7a8b-9c0d-1e2f-3a4b-5c6d7e8f9a0b",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_transaction_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
  "reimbursement_transaction_id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
  "reimbursement_amount": 12.50,
  "reimbursement_source": "Work expense reimbursement",
  "reimbursement_date": "2026-02-11",
  "status": "confirmed",
  "notes": "February expense report",
  "created_at": "2026-02-11T14:00:00Z",
  "created_by": "user"
}
```

**Example JSON (Partial Reimbursement - Many-to-One):**
```json
{
  "id": "6f7a8b9c-0d1e-2f3a-4b5c-6d7e8f9a0b1c",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_transaction_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "reimbursement_transaction_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "reimbursement_amount": 25.00,
  "reimbursement_source": "Friend: Sarah",
  "reimbursement_date": "2026-02-10",
  "status": "confirmed",
  "notes": "Her half of dinner ($50 total)",
  "created_at": "2026-02-10T20:00:00Z",
  "created_by": "user"
}
```

**Example JSON (Second Partial Reimbursement for Same Purchase):**
```json
{
  "id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "original_transaction_id": "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d",
  "reimbursement_transaction_id": "9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f",
  "reimbursement_amount": 25.00,
  "reimbursement_source": "Friend: Mike",
  "reimbursement_date": "2026-02-11",
  "status": "confirmed",
  "notes": "His half of dinner ($50 total)",
  "created_at": "2026-02-11T10:30:00Z",
  "created_by": "user"
}
```

**Many-to-One Example:**
- Original transaction: $100 dinner
- ReimbursementLink 1: $40 from Sarah
- ReimbursementLink 2: $30 from Mike
- ReimbursementLink 3: $30 from Emily
- Result: `original_transaction.reimbursed_amount = $100`, `reimbursement_status = 'full'`, `net_amount = $0`

---

### 8. RewardsProfile

Defines the rewards structure for a specific credit card at a point in time. **Supports time-dependent rewards** (e.g., rotating 5% categories).

**Fields:**

| Field                  | Type      | Constraints                 | Description                                           |
|------------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                   | UUID      | Primary Key                 | Unique rewards profile identifier                     |
| `payment_instrument_id`| UUID      | Foreign Key, Not Null       | Reference to `PaymentInstrument` (credit card only)   |
| `user_id`              | UUID      | Foreign Key, Not Null       | Reference to `User` (denormalized)                    |
| `profile_name`         | String    | Not Null                    | Profile name (e.g., "Q1 2026 Rewards")                |
| `valid_from`           | Date      | Not Null                    | Start date for this rewards structure                 |
| `valid_until`          | Date      | Nullable                    | End date (null = ongoing)                             |
| `default_rate`         | Decimal   | Not Null                    | Default cashback/points rate (e.g., 1.0 = 1%)         |
| `rate_type`            | Enum      | Not Null                    | Type: `cashback_percent`, `points_per_dollar`         |
| `category_rates`       | JSONB     | Not Null                    | Category-specific rates (see schema below)            |
| `annual_fee`           | Decimal   | Default: 0.00               | Annual fee for this card                              |
| `signup_bonus`         | Decimal   | Nullable                    | Signup bonus (points or dollars)                      |
| `created_at`           | Timestamp | Not Null                    | Profile creation timestamp                            |
| `updated_at`           | Timestamp | Not Null                    | Last update timestamp                                 |

**Category Rates JSON Schema:**
```json
{
  "dining": 3.0,
  "travel": 3.0,
  "groceries": 1.0,
  "gas": 1.0,
  "other": 1.0
}
```
- Keys: Category names (must match `NormalizedTransaction.category`)
- Values: Rate (e.g., 3.0 = 3% cashback or 3 points per dollar)

**Relationships:**
- `RewardsProfile` **belongs to** `PaymentInstrument`
- `RewardsProfile` **belongs to** `User`
- `RewardsProfile` **has many** `PointsTransaction` (for transactions within `valid_from` to `valid_until`)

**Constraints:**
- Index on `(payment_instrument_id, valid_from, valid_until)` for efficient date range queries
- Check constraint: `valid_until IS NULL OR valid_until >= valid_from`
- Only one active profile (where `valid_until IS NULL` or `valid_until >= CURRENT_DATE`) per `payment_instrument_id`

**Example JSON (Chase Sapphire Reserve):**
```json
{
  "id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "payment_instrument_id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_name": "Chase Sapphire Reserve - Standard",
  "valid_from": "2026-01-01",
  "valid_until": null,
  "default_rate": 1.0,
  "rate_type": "points_per_dollar",
  "category_rates": {
    "dining": 3.0,
    "travel": 3.0,
    "groceries": 1.0,
    "gas": 1.0,
    "entertainment": 1.0,
    "shopping": 1.0,
    "other": 1.0
  },
  "annual_fee": 550.00,
  "signup_bonus": 60000,
  "created_at": "2026-01-16T09:30:00Z",
  "updated_at": "2026-01-16T09:30:00Z"
}
```

**Example JSON (Discover It - Rotating 5% Q1 2026):**
```json
{
  "id": "9c0d1e2f-3a4b-5c6d-7e8f-9a0b1c2d3e4f",
  "payment_instrument_id": "a0b1c2d3-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "profile_name": "Discover It - Q1 2026 (Groceries 5%)",
  "valid_from": "2026-01-01",
  "valid_until": "2026-03-31",
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "groceries": 5.0,
    "dining": 1.0,
    "gas": 1.0,
    "travel": 1.0,
    "other": 1.0
  },
  "annual_fee": 0.00,
  "signup_bonus": null,
  "created_at": "2025-12-15T10:00:00Z",
  "updated_at": "2025-12-15T10:00:00Z"
}
```

---

### 9. PointsTransaction

Records rewards (points or cashback) earned for a specific transaction. **Immutable once created.**

**Fields:**

| Field                      | Type      | Constraints                 | Description                                           |
|----------------------------|-----------|-----------------------------|-------------------------------------------------------|
| `id`                       | UUID      | Primary Key                 | Unique points transaction identifier                  |
| `normalized_transaction_id`| UUID      | Foreign Key, Unique, Not Null | Reference to `NormalizedTransaction` (one-to-one) |
| `rewards_profile_id`       | UUID      | Foreign Key, Not Null       | Reference to `RewardsProfile` used for calculation    |
| `user_id`                  | UUID      | Foreign Key, Not Null       | Reference to `User` (denormalized)                    |
| `points_earned`            | Decimal   | Not Null                    | Points or cashback earned (e.g., 37.50)               |
| `rate_applied`             | Decimal   | Not Null                    | Rate used for calculation (e.g., 3.0)                 |
| `category_used`            | String    | Not Null                    | Category used for rate lookup (e.g., "dining")        |
| `rate_type`                | Enum      | Not Null                    | Type: `cashback_percent`, `points_per_dollar`         |
| `calculation_formula`      | String    | Not Null                    | Human-readable formula (e.g., "$12.50 × 3.0 = 37.5 points") |
| `created_at`               | Timestamp | Not Null                    | Points transaction creation timestamp                 |

**Calculation Logic:**
```
IF rate_type = 'points_per_dollar':
    points_earned = transaction.amount * rate_applied
ELIF rate_type = 'cashback_percent':
    points_earned = transaction.amount * (rate_applied / 100)
```

**Relationships:**
- `PointsTransaction` **belongs to** `NormalizedTransaction` (one-to-one)
- `PointsTransaction` **belongs to** `RewardsProfile`
- `PointsTransaction` **belongs to** `User`

**Constraints:**
- Unique index on `normalized_transaction_id` (one points transaction per purchase)
- Index on `(user_id, created_at)` for rewards aggregation queries
- `points_earned` precision: `DECIMAL(12, 2)`

**Example JSON:**
```json
{
  "id": "0d1e2f3a-4b5c-6d7e-8f9a-0b1c2d3e4f5a",
  "normalized_transaction_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
  "rewards_profile_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "points_earned": 37.50,
  "rate_applied": 3.0,
  "category_used": "dining",
  "rate_type": "points_per_dollar",
  "calculation_formula": "$12.50 × 3.0 points/dollar = 37.5 points",
  "created_at": "2026-02-11T12:00:21Z"
}
```

---

## Entity Relationship Diagram (ERD)

```
┌─────────────────────┐
│       User          │
│ ─────────────────── │
│ id (PK)             │
│ email               │
│ oauth_provider      │
│ oauth_subject_id    │
│ display_name        │
│ timezone            │
│ created_at          │
│ updated_at          │
│ deleted_at          │
└──────────┬──────────┘
           │
           │ 1:N
           ├───────────────────────────────────────┐
           │                                       │
           ▼                                       ▼
┌─────────────────────┐                ┌─────────────────────────┐
│   EmailAccount      │                │  PaymentInstrument      │
│ ─────────────────── │                │ ─────────────────────── │
│ id (PK)             │                │ id (PK)                 │
│ user_id (FK)        │                │ user_id (FK)            │
│ provider            │                │ type                    │
│ email_address       │                │ issuer                  │
│ oauth_refresh_token │ (encrypted)    │ display_name            │
│ oauth_access_token  │ (encrypted)    │ last_four_digits        │
│ sync_enabled        │                │ account_identifier      │
│ last_sync_at        │                │ network                 │
│ created_at          │                │ status                  │
└──────────┬──────────┘                │ created_at              │
           │                           └──────────┬──────────────┘
           │ 1:N                                  │
           │                                      │ 1:1 (credit cards only)
           ▼                                      │
┌─────────────────────┐                           ▼
│     RawEmail        │                ┌─────────────────────────┐
│ ─────────────────── │                │   RewardsProfile        │
│ id (PK)             │                │ ─────────────────────── │
│ email_account_id(FK)│                │ id (PK)                 │
│ user_id (FK)        │                │ payment_instrument_id(FK)│
│ message_id          │                │ user_id (FK)            │
│ sender_email        │                │ profile_name            │
│ subject             │                │ valid_from              │
│ received_at         │                │ valid_until             │
│ synced_at           │                │ default_rate            │
│ parsing_status      │                │ rate_type               │
│ parsing_error       │                │ category_rates (JSONB)  │
│ parsed_at           │                │ annual_fee              │
└──────────┬──────────┘                │ signup_bonus            │
           │                           │ created_at              │
           │ 1:1                       └──────────┬──────────────┘
           │                                      │
           ▼                                      │ 1:N
┌─────────────────────┐                           │
│  ParsedTransaction  │                           │
│ ─────────────────── │                           │
│ id (PK)             │                           │
│ raw_email_id (FK)   │                           │
│ user_id (FK)        │                           │
│ merchant_raw        │                           │
│ amount              │                           │
│ currency            │                           │
│ transaction_date    │                           │
│ transaction_type    │                           │
│ payment_instrument_ │                           │
│   hint              │                           │
│ transaction_id_     │                           │
│   external          │                           │
│ confidence_score    │                           │
│ created_at          │                           │
└──────────┬──────────┘                           │
           │                                      │
           │ 1:1                                  │
           │                                      │
           ▼                                      │
┌─────────────────────────────────────────────────┼─────────┐
│         NormalizedTransaction                   │         │
│ ───────────────────────────────────────────────────────  │
│ id (PK)                                         │         │
│ user_id (FK)                                    │         │
│ parsed_transaction_id (FK, nullable)            │         │
│ payment_instrument_id (FK) ─────────────────────┘         │
│ merchant_normalized                                       │
│ merchant_original                                         │
│ amount                                                    │
│ currency                                                  │
│ transaction_date                                          │
│ transaction_type                                          │
│ category                                                  │
│ category_confidence                                       │
│ status                                                    │
│ reimbursement_status                                      │
│ reimbursed_amount (computed)                              │
│ net_amount (computed)                                     │
│ notes                                                     │
│ source                                                    │
│ created_at                                                │
│ updated_at                                                │
│ version                                                   │
└──────────┬──────────────────────────────┬─────────────────┘
           │                              │
           │ 1:N                          │ 1:1
           │                              │
           ▼                              ▼
┌─────────────────────────┐   ┌─��───────────────────────┐
│  ReimbursementLink      │   │   PointsTransaction     │
│ ─────────────────────── │   │ ─────────────────────── │
│ id (PK)                 │   │ id (PK)                 │
│ user_id (FK)            │   │ normalized_transaction_ │
│ original_transaction_id │   │   id (FK)               │
│   (FK)                  │   │ rewards_profile_id (FK) ├───┐
│ reimbursement_          │   │ user_id (FK)            │   │
│   transaction_id (FK)   │   │ points_earned           │   │
│ reimbursement_amount    │   │ rate_applied            │   │
│ reimbursement_source    │   │ category_used           │   │
│ reimbursement_date      │   │ rate_type               │   │
│ status                  │   │ calculation_formula     │   │
│ notes                   │   │ created_at              │   │
│ created_at              │   └─────────────────────────┘   │
│ created_by              │                                 │
└─────────────────────────┘                                 │
                                                            │
  Many-to-one relationship:                                 │
  Multiple ReimbursementLinks can reference                 │
  the same original_transaction_id                          │
  (partial reimbursements from different sources)           │
                                                            │
                  ┌─────────────────────────────────────────┘
                  │
                  │ (FK relationship)
```

**Key Relationships:**
- **User → EmailAccount**: 1:N (one user can connect multiple email accounts)
- **User → PaymentInstrument**: 1:N (one user has multiple cards/P2P accounts)
- **EmailAccount → RawEmail**: 1:N (one email account receives many emails)
- **RawEmail → ParsedTransaction**: 1:1 (each email parsed into one transaction)
- **ParsedTransaction → NormalizedTransaction**: 1:1 (each parsed transaction normalized into one ledger entry)
- **PaymentInstrument → NormalizedTransaction**: 1:N (one card has many transactions)
- **PaymentInstrument → RewardsProfile**: 1:1 (active profile per card)
- **RewardsProfile → PointsTransaction**: 1:N (one profile used for many points calculations)
- **NormalizedTransaction → PointsTransaction**: 1:1 (each purchase earns points once)
- **NormalizedTransaction → ReimbursementLink**: 1:N (one purchase can have multiple partial reimbursements)

---

## Data Flow Example: Email to Ledger

### Scenario: Chase Sapphire Reserve transaction notification

**Step 1: Email Received**
```json
{
  "email": {
    "from": "no-reply@chase.com",
    "subject": "Your Chase card was used",
    "body": "Your Chase Sapphire Reserve card ending in 5678 was used for a $12.50 transaction at SQ *BLUE BOTTLE COFFEE on 02/10/2026."
  }
}
```

**Step 2: RawEmail Created**
```json
{
  "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "email_account_id": "7c9e6c7a-3b5f-4d2e-9f1a-8b6c5d4e3f2a",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "message_id": "gmail-msg-187a3b2c1d0e9f8g",
  "sender_email": "no-reply@chase.com",
  "subject": "Your Chase card was used",
  "received_at": "2026-02-10T14:22:30Z",
  "synced_at": "2026-02-11T12:00:15Z",
  "parsing_status": "success"
}
```

**Step 3: ParsedTransaction Created**
```json
{
  "id": "2b3c4d5e-6f7a-8b9c-0d1e-2f3a4b5c6d7e",
  "raw_email_id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "merchant_raw": "SQ *BLUE BOTTLE COFFEE",
  "amount": 12.50,
  "transaction_date": "2026-02-10",
  "transaction_type": "purchase",
  "payment_instrument_hint": "5678",
  "confidence_score": 95
}
```

**Step 4: PaymentInstrument Matched** (by last 4 digits "5678")
```json
{
  "id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "display_name": "Chase Sapphire Reserve",
  "last_four_digits": "5678"
}
```

**Step 5: NormalizedTransaction Created**
```json
{
  "id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "payment_instrument_id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "merchant_normalized": "Blue Bottle Coffee",
  "merchant_original": "SQ *BLUE BOTTLE COFFEE",
  "amount": 12.50,
  "transaction_date": "2026-02-10",
  "category": "Dining",
  "category_confidence": 95,
  "status": "settled",
  "reimbursement_status": "none",
  "net_amount": 12.50,
  "source": "email_parsed"
}
```

**Step 6: RewardsProfile Lookup** (for Chase Sapphire Reserve, valid on 2026-02-10)
```json
{
  "id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "payment_instrument_id": "9f3b8a6c-5d2e-4f1a-8b7c-6d5e4f3a2b1c",
  "rate_type": "points_per_dollar",
  "category_rates": {
    "dining": 3.0
  }
}
```

**Step 7: PointsTransaction Created**
```json
{
  "id": "0d1e2f3a-4b5c-6d7e-8f9a-0b1c2d3e4f5a",
  "normalized_transaction_id": "3c4d5e6f-7a8b-9c0d-1e2f-3a4b5c6d7e8f",
  "rewards_profile_id": "8b9c0d1e-2f3a-4b5c-6d7e-8f9a0b1c2d3e",
  "points_earned": 37.50,
  "rate_applied": 3.0,
  "category_used": "dining",
  "calculation_formula": "$12.50 × 3.0 points/dollar = 37.5 points"
}
```

**Step 8: User Views Transaction**
Frontend displays:
- **Merchant**: Blue Bottle Coffee
- **Amount**: $12.50
- **Card**: Chase Sapphire Reserve (••5678)
- **Category**: Dining (95% confident)
- **Rewards**: 37.5 points (3× dining)
- **Net Amount**: $12.50 (no reimbursements)

---

## Reimbursement Example: Partial Many-to-One

### Scenario: $100 dinner split 4 ways (you pay, 3 friends reimburse)

**Step 1: Original Transaction**
```json
{
  "id": "txn-dinner-001",
  "merchant_normalized": "Fancy Restaurant",
  "amount": 100.00,
  "payment_instrument_id": "chase-sapphire-5678",
  "transaction_date": "2026-02-08",
  "reimbursed_amount": 0.00,
  "net_amount": 100.00,
  "reimbursement_status": "none"
}
```

**Step 2: First Reimbursement (Venmo from Sarah - $25)**
```json
{
  "reimbursement_link": {
    "id": "reimb-001",
    "original_transaction_id": "txn-dinner-001",
    "reimbursement_transaction_id": "txn-venmo-sarah",
    "reimbursement_amount": 25.00,
    "reimbursement_source": "Friend: Sarah",
    "reimbursement_date": "2026-02-09",
    "status": "confirmed"
  }
}
```
**Original Transaction Updated** (via trigger):
```json
{
  "id": "txn-dinner-001",
  "reimbursed_amount": 25.00,
  "net_amount": 75.00,
  "reimbursement_status": "partial"
}
```

**Step 3: Second Reimbursement (Zelle from Mike - $25)**
```json
{
  "reimbursement_link": {
    "id": "reimb-002",
    "original_transaction_id": "txn-dinner-001",
    "reimbursement_transaction_id": "txn-zelle-mike",
    "reimbursement_amount": 25.00,
    "reimbursement_source": "Friend: Mike",
    "reimbursement_date": "2026-02-10",
    "status": "confirmed"
  }
}
```
**Original Transaction Updated**:
```json
{
  "id": "txn-dinner-001",
  "reimbursed_amount": 50.00,
  "net_amount": 50.00,
  "reimbursement_status": "partial"
}
```

**Step 4: Third Reimbursement (Cash App from Emily - $25)**
```json
{
  "reimbursement_link": {
    "id": "reimb-003",
    "original_transaction_id": "txn-dinner-001",
    "reimbursement_transaction_id": "txn-cashapp-emily",
    "reimbursement_amount": 25.00,
    "reimbursement_source": "Friend: Emily",
    "reimbursement_date": "2026-02-11",
    "status": "confirmed"
  }
}
```
**Original Transaction Updated**:
```json
{
  "id": "txn-dinner-001",
  "reimbursed_amount": 75.00,
  "net_amount": 25.00,
  "reimbursement_status": "partial"
}
```

**Frontend Display (Side-by-Side View):**
```
┌─────────────────────────────────────────────────────────┐
│ Original Transaction                                    │
├─────────────────────────────────────────────────────────┤
│ Merchant: Fancy Restaurant                              │
│ Date: 2026-02-08                                        │
│ Amount: $100.00                                         │
│ Card: Chase Sapphire Reserve (••5678)                   │
│ Category: Dining                                        │
│ Rewards: 300 points (3×)                                │
├─────────────────────────────────────────────────────────┤
│ Reimbursements                                          │
├─────────────────────────────────────────────────────────┤
│ ✓ Sarah (Venmo) - $25.00 on 2026-02-09                  │
│ ✓ Mike (Zelle) - $25.00 on 2026-02-10                   │
│ ✓ Emily (Cash App) - $25.00 on 2026-02-11               │
├─────────────────────────────────────────────────────────┤
│ Net Amount: $25.00 (75% reimbursed)                     │
└─────────────────────────────────────────────────────────┘
```

---

## Time-Dependent Rewards Example

### Scenario: Discover It Rotating 5% Categories

**Q1 2026: Groceries 5%**
```json
{
  "rewards_profile": {
    "id": "profile-discover-q1-2026",
    "payment_instrument_id": "discover-1234",
    "valid_from": "2026-01-01",
    "valid_until": "2026-03-31",
    "category_rates": {
      "groceries": 5.0,
      "other": 1.0
    }
  }
}
```

**Q2 2026: Gas 5%**
```json
{
  "rewards_profile": {
    "id": "profile-discover-q2-2026",
    "payment_instrument_id": "discover-1234",
    "valid_from": "2026-04-01",
    "valid_until": "2026-06-30",
    "category_rates": {
      "gas": 5.0,
      "other": 1.0
    }
  }
}
```

**Transaction on 2026-03-15 (Grocery Store - Q1 Profile Applied)**
```json
{
  "normalized_transaction": {
    "id": "txn-001",
    "amount": 50.00,
    "transaction_date": "2026-03-15",
    "category": "groceries"
  },
  "points_transaction": {
    "rewards_profile_id": "profile-discover-q1-2026",
    "rate_applied": 5.0,
    "points_earned": 2.50,
    "calculation_formula": "$50.00 × 5% = $2.50 cashback"
  }
}
```

**Transaction on 2026-04-10 (Grocery Store - Q2 Profile Applied)**
```json
{
  "normalized_transaction": {
    "id": "txn-002",
    "amount": 50.00,
    "transaction_date": "2026-04-10",
    "category": "groceries"
  },
  "points_transaction": {
    "rewards_profile_id": "profile-discover-q2-2026",
    "rate_applied": 1.0,
    "points_earned": 0.50,
    "calculation_formula": "$50.00 × 1% = $0.50 cashback"
  }
}
```

**Rewards Optimization Suggestion (Q2 2026):**
```
"You spent $50.00 on groceries using Discover It (1% cashback).
If you had used Chase Sapphire Reserve (1× on groceries = 1 point = ~$0.015 value),
you would have earned $0.50 in points (similar).

However, in Q1 2026, this same purchase would have earned $2.50 with Discover It!"
```

---

## Database Schema Notes

### Indexes (Performance)

**High-Priority Indexes:**
1. `normalized_transactions (user_id, transaction_date DESC)` - for date range queries
2. `normalized_transactions (user_id, payment_instrument_id)` - for per-card views
3. `normalized_transactions (user_id, category)` - for spending by category
4. `reimbursement_links (original_transaction_id)` - for reimbursement lookups
5. `points_transactions (user_id, created_at DESC)` - for rewards aggregation
6. `rewards_profiles (payment_instrument_id, valid_from, valid_until)` - for time-based lookups

**Unique Constraints:**
1. `users (oauth_provider, oauth_subject_id)` - prevent duplicate accounts
2. `email_accounts (user_id, email_address)` - one email per user
3. `raw_emails (message_id)` - prevent duplicate email processing
4. `parsed_transactions (raw_email_id)` - one parsed transaction per email
5. `points_transactions (normalized_transaction_id)` - one points record per transaction

### Triggers (Automation)

**Trigger 1: Update Reimbursed Amount**
```sql
CREATE TRIGGER update_reimbursed_amount
AFTER INSERT OR UPDATE OR DELETE ON reimbursement_links
FOR EACH ROW
EXECUTE FUNCTION recalculate_reimbursed_amount();
```
Function: Sum all `reimbursement_amount` for `status = 'confirmed'` and update `normalized_transactions.reimbursed_amount`

**Trigger 2: Update Reimbursement Status**
```sql
CREATE TRIGGER update_reimbursement_status
AFTER UPDATE OF reimbursed_amount ON normalized_transactions
FOR EACH ROW
EXECUTE FUNCTION update_reimbursement_status();
```
Function: Set `reimbursement_status` to:
- `none` if `reimbursed_amount = 0`
- `partial` if `0 < reimbursed_amount < amount`
- `full` if `reimbursed_amount >= amount`

**Trigger 3: Increment Version on Update**
```sql
CREATE TRIGGER increment_version
BEFORE UPDATE ON normalized_transactions
FOR EACH ROW
EXECUTE FUNCTION increment_version();
```
Function: Increment `version` and update `updated_at` timestamp

### Audit Trail (TransactionAuditLog)

**TransactionAuditLog Table** (separate from core model for traceability):
```json
{
  "id": "audit-001",
  "normalized_transaction_id": "txn-001",
  "user_id": "user-123",
  "changed_by": "user",
  "change_type": "update",
  "field_changed": "category",
  "old_value": "Shopping",
  "new_value": "Groceries",
  "reason": "User correction",
  "timestamp": "2026-02-11T15:00:00Z"
}
```

---

## API Query Examples

### Query 1: Get all transactions for user in February 2026
```sql
SELECT *
FROM normalized_transactions
WHERE user_id = '550e8400-e29b-41d4-a716-446655440000'
  AND transaction_date BETWEEN '2026-02-01' AND '2026-02-29'
ORDER BY transaction_date DESC;
```

### Query 2: Get net spending by category (after reimbursements)
```sql
SELECT
  category,
  SUM(amount) AS gross_spending,
  SUM(reimbursed_amount) AS total_reimbursed,
  SUM(net_amount) AS net_spending
FROM normalized_transactions
WHERE user_id = '550e8400-e29b-41d4-a716-446655440000'
  AND transaction_date BETWEEN '2026-02-01' AND '2026-02-29'
GROUP BY category
ORDER BY net_spending DESC;
```

### Query 3: Get total rewards earned per card this month
```sql
SELECT
  pi.display_name AS card_name,
  SUM(pt.points_earned) AS total_points
FROM points_transactions pt
JOIN normalized_transactions nt ON pt.normalized_transaction_id = nt.id
JOIN payment_instruments pi ON nt.payment_instrument_id = pi.id
WHERE nt.user_id = '550e8400-e29b-41d4-a716-446655440000'
  AND nt.transaction_date BETWEEN '2026-02-01' AND '2026-02-29'
GROUP BY pi.id, pi.display_name
ORDER BY total_points DESC;
```

### Query 4: Get pending reimbursements
```sql
SELECT
  nt.merchant_normalized,
  nt.amount,
  nt.reimbursed_amount,
  (nt.amount - nt.reimbursed_amount) AS pending_reimbursement,
  rl.reimbursement_source,
  rl.reimbursement_date AS expected_date
FROM normalized_transactions nt
JOIN reimbursement_links rl ON nt.id = rl.original_transaction_id
WHERE nt.user_id = '550e8400-e29b-41d4-a716-446655440000'
  AND rl.status = 'expected'
ORDER BY rl.reimbursement_date;
```

### Query 5: Rewards optimization (missed rewards)
```sql
-- Find transactions where user could have earned more rewards with a different card
WITH transaction_rewards AS (
  SELECT
    nt.id,
    nt.merchant_normalized,
    nt.amount,
    nt.category,
    pi.display_name AS card_used,
    pt.points_earned,
    rp.rate_applied AS rate_used
  FROM normalized_transactions nt
  JOIN payment_instruments pi ON nt.payment_instrument_id = pi.id
  JOIN points_transactions pt ON nt.id = pt.normalized_transaction_id
  JOIN rewards_profiles rp ON pt.rewards_profile_id = rp.id
  WHERE nt.user_id = '550e8400-e29b-41d4-a716-446655440000'
    AND nt.transaction_date BETWEEN '2026-02-01' AND '2026-02-29'
),
better_rewards AS (
  SELECT
    tr.id,
    tr.merchant_normalized,
    tr.amount,
    tr.category,
    tr.card_used,
    tr.points_earned AS actual_points,
    pi_alt.display_name AS better_card,
    (tr.amount * (rp_alt.category_rates->>tr.category)::DECIMAL) AS potential_points
  FROM transaction_rewards tr
  CROSS JOIN payment_instruments pi_alt
  JOIN rewards_profiles rp_alt ON pi_alt.id = rp_alt.payment_instrument_id
  WHERE pi_alt.user_id = '550e8400-e29b-41d4-a716-446655440000'
    AND rp_alt.valid_from <= tr.transaction_date
    AND (rp_alt.valid_until IS NULL OR rp_alt.valid_until >= tr.transaction_date)
    AND (rp_alt.category_rates->>tr.category)::DECIMAL > tr.rate_used
)
SELECT
  merchant_normalized,
  amount,
  card_used,
  actual_points,
  better_card,
  potential_points,
  (potential_points - actual_points) AS missed_points
FROM better_rewards
WHERE potential_points > actual_points
ORDER BY missed_points DESC;
```

---

## Next Steps

1. **Implement Database Migrations** (Alembic for PostgreSQL)
   - Create migration scripts for all tables
   - Add indexes, constraints, and triggers
   - Test migrations on dev environment

2. **Define Pydantic Models** (Backend)
   - Map each entity to a Pydantic model
   - Add validation rules (e.g., `reimbursed_amount <= amount`)
   - Generate OpenAPI schema

3. **Generate TypeScript Types** (Frontend)
   - Use Pydantic → TypeScript generator (e.g., `pydantic-to-typescript`)
   - Place in `shared/types/` for type safety

4. **Build Repository Layer** (Backend)
   - Implement CRUD operations for each entity
   - Add complex queries (net spending, rewards aggregation)
   - Write unit tests for repository functions

5. **Document Edge Cases**
   - Refund handling (negative amounts? separate transaction type?)
   - Timezone handling for transaction dates
   - Multi-currency conversions (V2)
   - Duplicate detection edge cases

---

## Document History

| Version | Date       | Author      | Changes                          |
|---------|------------|-------------|----------------------------------|
| 1.0     | 2026-02-11 | Engineering | Initial domain model definition  |

---

**Questions? Contact**: engineering@spendi.app