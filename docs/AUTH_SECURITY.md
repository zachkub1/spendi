# Authentication & Security Model: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Security & Engineering

---

## Overview

Spendi's security model is built on three core principles:

1. **Zero Trust**: Never trust user input; always validate and sanitize
2. **Least Privilege**: Grant minimal permissions required for functionality
3. **Defense in Depth**: Multiple layers of security controls

This document defines authentication flows, token management, encryption strategies, and threat mitigations.

---

## Table of Contents

1. [OAuth Authentication Flow](#oauth-authentication-flow)
2. [Token Storage Strategy](#token-storage-strategy)
3. [Encryption Architecture](#encryption-architecture)
4. [Gmail API Scopes & Permissions](#gmail-api-scopes--permissions)
5. [Session Management](#session-management)
6. [Audit Trail](#audit-trail)
7. [Threat Model & Mitigations](#threat-model--mitigations)
8. [What is NEVER Stored](#what-is-never-stored)
9. [FastAPI Implementation Guide](#fastapi-implementation-guide)
10. [Security Checklist](#security-checklist)

---

## OAuth Authentication Flow

### Two-Step OAuth Consent

Spendi uses a **two-step consent flow** to separate user authentication from Gmail API access:

1. **Step 1: User Authentication** - Login with Google (minimal scopes)
2. **Step 2: Gmail Access** - Explicit consent to read transaction emails (after user understands purpose)

This approach:
- Builds trust by explaining data usage before requesting access
- Allows users to authenticate without granting email access (for future features like manual entry)
- Complies with OAuth best practices (incremental authorization)

---

### Flow 1: Initial Sign-Up (New User)

```
┌──────────────────────────────────────────────────────────────────────┐
│ User                                                                 │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 1. Click "Sign Up with Google"
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend (Next.js)                                          │
│ - Redirects to /api/auth/google/authorize                           │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 2. Redirect to Google OAuth consent
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Google OAuth Server                                                  │
│ - Requested Scopes: openid, email, profile                          │
│ - User sees: "Spendi wants to access your Google account"         │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 3. User grants consent
        │ 4. Redirect to /api/auth/google/callback?code=AUTH_CODE
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Backend (FastAPI)                                           │
│ - Exchange AUTH_CODE for access_token + id_token                     │
│ - Verify id_token signature (RS256)                                  │
│ - Extract user info: email, sub (subject ID), name                   │
│ - Create or update User record                                       │
│ - Generate session token (JWT)                                       │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 5. Set httpOnly cookie with session token
        │ 6. Redirect to /dashboard
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend (Dashboard)                                        │
│ - Shows onboarding: "Connect your email to sync transactions"       │
│ - Button: "Connect Gmail"                                            │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 7. User clicks "Connect Gmail"
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend                                                    │
│ - Redirects to /api/auth/google/authorize-gmail                     │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 8. Redirect to Google OAuth consent (with Gmail scope)
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Google OAuth Server                                                  │
│ - Requested Scopes: https://www.googleapis.com/auth/gmail.readonly  │
│ - User sees: "Spendi wants to read your emails"                   │
│ - Shows detailed permissions explanation                             │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 9. User grants consent
        │ 10. Redirect to /api/auth/google/gmail-callback?code=AUTH_CODE
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Backend (FastAPI)                                           │
│ - Exchange AUTH_CODE for access_token + refresh_token                │
│ - Encrypt refresh_token using envelope encryption                    │
│ - Create EmailAccount record with encrypted tokens                   │
│ - Log audit event: "Gmail access granted"                            │
│ - Trigger initial email sync job                                     │
└───────┬──────────────────��───────────────────────────────────────────┘
        │
        │ 11. Redirect to /dashboard (with success message)
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend (Dashboard)                                        │
│ - Shows "Email connected! Syncing transactions..."                   │
│ - Displays transaction list as data arrives                          │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Two separate OAuth flows**: One for authentication, one for Gmail access
- **Incremental authorization**: User understands purpose before granting email access
- **Refresh tokens only for Gmail**: Session tokens for user authentication (short-lived)
- **Audit logging**: Every token grant/revoke logged with timestamp

---

### Flow 2: Returning User Login

```
┌──────────────────────────────────────────────────────────────────────┐
│ User                                                                 │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 1. Click "Login with Google"
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend                                                    │
│ - Redirects to /api/auth/google/authorize                           │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 2. Redirect to Google OAuth (may skip consent if already granted)
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Google OAuth Server                                                  │
│ - User already consented, auto-approves                              │
│ - Redirect to /api/auth/google/callback?code=AUTH_CODE              │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 3. Exchange code for tokens, verify identity
        │ 4. Lookup existing User by oauth_subject_id
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Backend                                                     │
│ - Generate new session token                                         │
│ - Update last_login timestamp                                        │
│ - Log audit event: "User logged in"                                  │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 5. Set httpOnly cookie, redirect to /dashboard
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Dashboard                                                   │
│ - User sees their transaction history                                │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **No password**: Spendi never handles passwords (delegated to Google)
- **Fast login**: Google auto-approves if user already consented
- **Session expiry**: Sessions expire after 7 days of inactivity (configurable)

---

### Flow 3: Revoking Gmail Access

```
┌──────────────────────────────────────────────────────────────────────┐
│ User (in Spendi Settings)                                          │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 1. Click "Disconnect Gmail"
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend                                                    │
│ - Confirm: "Are you sure? Transaction sync will stop."              │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 2. User confirms
        │ 3. POST /api/email-accounts/{id}/revoke
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Backend                                                     │
│ - Verify user owns this EmailAccount                                 │
│ - Decrypt refresh_token                                              │
│ - Revoke token at Google (POST to revocation endpoint)              │
│ - Delete encrypted tokens from database                              │
│ - Set EmailAccount.sync_enabled = false                              │
│ - Log audit event: "Gmail access revoked"                            │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 4. Return success
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend                                                    │
│ - Show "Gmail disconnected. Your transaction history remains."      │
│ - Offer "Reconnect Gmail" button                                     │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Graceful revocation**: Tokens revoked at Google, then deleted locally
- **Data preservation**: Existing transactions remain; only future sync stops
- **Audit trail**: Revocation logged with timestamp and reason

---

### Flow 4: Deleting Account (GDPR Compliance)

```
┌──────────────────────────────────────────────────────────────────────┐
│ User (in Spendi Settings)                                          │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 1. Click "Delete My Account"
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Frontend                                                    │
│ - Show warning: "This will delete ALL data. Export first?"          │
│ - Require re-authentication (confirm with Google)                    │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 2. User re-authenticates and confirms
        │ 3. POST /api/users/me/delete
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Backend                                                     │
│ - Verify user identity (check session token)                         │
│ - Revoke all OAuth tokens (Gmail + authentication)                   │
│ - Soft-delete User record (set deleted_at timestamp)                 │
│ - Cascade soft-delete all related records:                           │
│   - EmailAccounts, PaymentInstruments, Transactions, etc.           │
│ - Schedule hard-delete job (30 days later)                           │
│ - Log audit event: "Account deleted"                                 │
│ - Send confirmation email                                            │
└───────┬──────────────────────────────────────────────────────────────┘
        │
        │ 4. Destroy session, redirect to homepage
        ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Spendi Homepage                                                    │
│ - Show "Account deleted. Data will be purged in 30 days."           │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Points:**
- **Re-authentication required**: Prevents accidental deletions
- **Soft delete + grace period**: 30-day window to recover account
- **Hard delete after 30 days**: Automated job purges all data (GDPR compliant)
- **Token revocation**: All OAuth tokens revoked at Google

---

## Token Storage Strategy

### Token Types & Lifecycle

| Token Type          | Purpose                        | Lifetime           | Storage Location           | Encryption      |
|---------------------|--------------------------------|--------------------|----------------------------|-----------------|
| **Google ID Token** | User authentication (JWT)      | 1 hour             | Not stored (verified once) | N/A             |
| **Session Token**   | Spendi session (JWT)         | 7 days (idle)      | httpOnly cookie            | Signed (HS256)  |
| **Access Token**    | Gmail API access (short-lived) | 1 hour             | DB (EmailAccount table)    | AES-256 (envelope) |
| **Refresh Token**   | Gmail API refresh (long-lived) | No expiration      | DB (EmailAccount table)    | AES-256 (envelope) |

---

### Session Token (Spendi JWT)

**Purpose**: Maintain user session without storing passwords

**Issued**: After successful Google OAuth authentication

**Payload**:
```json
{
  "sub": "user-uuid-here",
  "email": "john.doe@gmail.com",
  "iat": 1707651600,
  "exp": 1708256400,
  "jti": "session-jti-unique-id"
}
```

**Storage**:
- **Client**: `httpOnly`, `Secure`, `SameSite=Lax` cookie
- **Server**: JTI stored in Redis with expiration (for revocation)

**Security Features**:
- **httpOnly**: Prevents XSS attacks (JavaScript cannot access)
- **Secure**: Only sent over HTTPS
- **SameSite=Lax**: CSRF protection
- **Short-lived**: 7 days idle timeout, 30 days absolute max
- **Revocable**: JTI blacklist in Redis for immediate invalidation

**Signing Algorithm**: HS256 (HMAC with SHA-256)
- Secret key: 256-bit random key stored in environment variable
- Rotated quarterly (automated process)

---

### Gmail Access Token (Short-Lived)

**Purpose**: Make authenticated Gmail API requests

**Issued**: By Google OAuth server

**Lifetime**: 1 hour

**Storage**:
- Table: `email_accounts`
- Column: `oauth_access_token` (encrypted)
- Encryption: AES-256 (envelope encryption)

**Refresh Logic**:
```python
# Before each Gmail API call:
if access_token_expired():
    access_token = refresh_access_token(refresh_token)
    update_email_account(access_token, expires_at)
```

**Security Features**:
- Encrypted at rest (even if DB compromised, tokens unusable without DEK)
- Automatic refresh on expiry
- Never logged or exposed in errors

---

### Gmail Refresh Token (Long-Lived)

**Purpose**: Obtain new access tokens without user re-authentication

**Issued**: By Google OAuth server (only on initial consent)

**Lifetime**: No expiration (revoked explicitly or on security events)

**Storage**:
- Table: `email_accounts`
- Column: `oauth_refresh_token` (encrypted)
- Encryption: AES-256 (envelope encryption)

**Critical Security Measures**:
1. **Envelope Encryption** (see below)
2. **Never transmitted to client** (server-side only)
3. **Revoked immediately** on:
   - User revokes Gmail access
   - User deletes account
   - Suspicious activity detected (e.g., token leaked)
4. **Audit log** on every use

**Google Security Features**:
- Google automatically revokes refresh tokens if:
  - User changes password
  - User revokes app access in Google Account settings
  - Token hasn't been used in 6 months (inactive)

---

## Encryption Architecture

### Envelope Encryption for OAuth Tokens

Spendi uses **envelope encryption** to protect OAuth refresh tokens at rest. This is a two-layer encryption approach:

```
┌────────────────────────────────────────────────────────────────┐
│                     Envelope Encryption                        │
└────────────────────────────────────────────────────────────────┘

Layer 1: Data Encryption Key (DEK)
- Unique 256-bit AES key per user
- Used to encrypt user's refresh tokens
- Stored encrypted in database

Layer 2: Key Encryption Key (KEK)
- Master key stored in AWS KMS / GCP Secret Manager
- Used to encrypt DEKs
- Never stored in application database
- Rotated annually
```

**Flow Diagram:**

```
┌─────────────────────────���────────────────────────────────────────────┐
│ Encrypting a Refresh Token                                          │
└──────────────────────────────────────────────────────────────────────┘

1. User grants Gmail access
   refresh_token = "ya29.abc123xyz..."

2. Generate DEK (Data Encryption Key)
   dek = random_bytes(32)  # 256-bit key

3. Encrypt refresh token with DEK
   encrypted_token = AES256_GCM_encrypt(
       plaintext=refresh_token,
       key=dek,
       iv=random_iv()
   )
   # Result: ciphertext + auth_tag

4. Encrypt DEK with KEK (from KMS)
   encrypted_dek = kms.encrypt(
       plaintext=dek,
       key_id="arn:aws:kms:us-east-1:123456789012:key/abcd-1234"
   )

5. Store in database:
   email_accounts.oauth_refresh_token = base64(encrypted_token)
   email_accounts.encryption_key = base64(encrypted_dek)
   email_accounts.encryption_iv = base64(iv)

┌──────────────────────────────────────────────────────────────────────┐
│ Decrypting a Refresh Token                                          │
└──────────────────────────────────────────────────────────────────────┘

1. Load from database:
   encrypted_token = base64_decode(email_accounts.oauth_refresh_token)
   encrypted_dek = base64_decode(email_accounts.encryption_key)
   iv = base64_decode(email_accounts.encryption_iv)

2. Decrypt DEK using KMS
   dek = kms.decrypt(
       ciphertext=encrypted_dek
   )

3. Decrypt refresh token using DEK
   refresh_token = AES256_GCM_decrypt(
       ciphertext=encrypted_token,
       key=dek,
       iv=iv
   )

4. Use refresh token to get access token
   response = google_oauth.refresh(refresh_token)
   access_token = response.access_token
```

**Why Envelope Encryption?**
- ✅ **DEK per user**: If one DEK is compromised, only that user's tokens are at risk
- ✅ **KEK in KMS**: Master key never leaves secure hardware (HSM)
- ✅ **Key rotation**: Can rotate KEK without re-encrypting all tokens (only re-encrypt DEKs)
- ✅ **Compliance**: Meets PCI DSS, HIPAA, GDPR encryption requirements

---

### Key Management with AWS KMS / GCP Secret Manager

**Key Hierarchy:**

```
┌──────────────────────────────────────────────────────────────┐
│ AWS KMS (or GCP Secret Manager)                              │
│ ────────────────────────────────────────────────────────────  │
│ Master Key (KEK): arn:aws:kms:region:account:key/xyz        │
│ - 256-bit AES key                                            │
│ - Stored in Hardware Security Module (HSM)                   │
│ - Automatic rotation every 365 days                          │
│ - Access controlled via IAM policies                         │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ Encrypts/Decrypts
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ PostgreSQL Database (email_accounts table)                   │
│ ────────────────────────────────────────────────────────────  │
│ Per-User DEK (encrypted):                                    │
│ - user_123: ENC[aes256:...]  ← encrypted with KEK           │
│ - user_456: ENC[aes256:...]  ← encrypted with KEK           │
│ - user_789: ENC[aes256:...]  ← encrypted with KEK           │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ Encrypts/Decrypts
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ OAuth Refresh Tokens (plaintext, in memory only)             │
│ - Never written to disk                                      │
│ - Used immediately, then discarded                           │
└──────────────────────────────────────────────────────────────┘
```

**IAM Policy (Least Privilege)**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:Encrypt"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/abcd-1234",
      "Condition": {
        "StringEquals": {
          "kms:EncryptionContext:purpose": "oauth-token-encryption"
        }
      }
    }
  ]
}
```

**Encryption Context** (additional security):
- Purpose: `oauth-token-encryption`
- User ID: `user-uuid-here`
- Timestamp: `1707651600`

This ensures KEK can only be used for its intended purpose.

---

## Gmail API Scopes & Permissions

### Least-Privilege Scopes

Spendi requests the **minimum Gmail API scopes** necessary:

| Scope                                           | Purpose                                  | Risk Level |
|-------------------------------------------------|------------------------------------------|------------|
| `openid`                                        | User authentication (required for OAuth) | Low        |
| `email`                                         | Access user's email address              | Low        |
| `profile`                                       | Access user's name and profile picture   | Low        |
| `https://www.googleapis.com/auth/gmail.readonly`| **Read-only** Gmail access               | Medium     |

**NOT Requested:**
- ❌ `gmail.modify` - No ability to modify emails
- ❌ `gmail.compose` - No ability to send emails
- ❌ `gmail.send` - No ability to send emails
- ❌ Full Gmail access - No unrestricted access

---

### Gmail.Readonly: What It Includes

The `gmail.readonly` scope allows Spendi to:

✅ **Allowed:**
- List messages (subject, sender, date, message ID)
- Read message content (body, attachments)
- Search messages by query (e.g., `from:chase.com`)
- Access message metadata (labels, thread ID)

❌ **NOT Allowed:**
- Modify messages (mark as read, delete, archive)
- Send messages
- Create drafts
- Modify labels
- Access Google Drive, Calendar, or other services

---

### Filtering to Transaction Emails Only

To minimize privacy concerns, Spendi **only reads transaction-related emails**:

**Allowlist Approach:**
```python
ALLOWED_SENDERS = [
    "no-reply@chase.com",
    "alerts@chase.com",
    "notifications@americanexpress.com",
    "citi.com",
    "discover.com",
    "venmo.com",
    "zelle.com",
    "cash.app"
]

# Gmail API query (server-side)
query = " OR ".join([f"from:{sender}" for sender in ALLOWED_SENDERS])
# Example: "from:no-reply@chase.com OR from:alerts@chase.com OR ..."

messages = gmail_service.users().messages().list(
    userId='me',
    q=query,
    maxResults=100
).execute()
```

**Privacy Guarantee:**
- Spendi **NEVER** queries personal emails (from friends, family, coworkers)
- Only emails from known financial institutions are fetched
- Email **content** is never stored (only extracted transaction fields)

---

### User Transparency: What Access Means

**In-App Explanation (Before Granting Gmail Access):**

```
┌────────────────────────────────────────────────────────────────┐
│ Connect Your Email                                             │
├────────────────────────────────────────────────────────────────┤
│ Spendi needs read-only access to your Gmail to              │
│ automatically sync transaction notifications.                  │
│                                                                 │
│ ✅ What we do:                                                 │
│    • Read transaction emails from banks and payment apps       │
│    • Extract merchant, amount, and date                        │
│    • Delete the email content (keep transaction data only)     │
│                                                                 │
│ ❌ What we DON'T do:                                           │
│    • Read personal emails (only financial institutions)        │
│    • Store full email content (privacy-first)                  │
│    • Send emails or modify your inbox                          │
│    • Share your data with third parties                        │
│                                                                 │
│ You can revoke access anytime in Settings.                     │
│                                                                 │
│ [Connect Gmail]   [Learn More]                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Session Management

### Session Lifecycle

**Creation:**
- User logs in via Google OAuth
- Server generates JWT session token (HS256)
- Token stored in `httpOnly`, `Secure`, `SameSite=Lax` cookie

**Validation (On Every Request):**
```python
def validate_session(request):
    token = request.cookies.get("session_token")
    if not token:
        raise Unauthorized("No session token")

    # Verify JWT signature
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

    # Check expiration
    if payload["exp"] < time.time():
        raise Unauthorized("Session expired")

    # Check revocation (JTI blacklist in Redis)
    if redis.sismember("revoked_sessions", payload["jti"]):
        raise Unauthorized("Session revoked")

    # Check user exists and not deleted
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or user.deleted_at:
        raise Unauthorized("User not found")

    return user
```

**Refresh:**
- Session tokens have 7-day idle timeout
- On activity, issue new token with extended expiry (rolling session)
- Old token remains valid until expiry (avoid breaking concurrent requests)

**Revocation:**
- User logs out: Add JTI to Redis blacklist, clear cookie
- User deletes account: Revoke all sessions (by user ID)
- Security event: Revoke all sessions for affected users

---

### Cookie Security

**Session Cookie Attributes:**
```python
response.set_cookie(
    key="session_token",
    value=jwt_token,
    httponly=True,       # Prevent XSS
    secure=True,         # HTTPS only
    samesite="Lax",      # CSRF protection
    max_age=604800,      # 7 days (seconds)
    domain="spendi.app",
    path="/"
)
```

**SameSite Options:**
- `Lax`: Cookies sent on top-level navigation (e.g., clicking a link) but not on cross-site subrequests (e.g., images, iframes)
- Prevents CSRF attacks while allowing normal navigation
- More permissive than `Strict`, more secure than `None`

---

## Audit Trail

### Audit Log Events

Every security-sensitive action is logged in an immutable audit log.

**Table: `audit_logs`**

| Field           | Type      | Description                                  |
|-----------------|-----------|----------------------------------------------|
| `id`            | UUID      | Unique audit log entry ID                    |
| `user_id`       | UUID      | User who performed the action                |
| `action`        | Enum      | Action type (see below)                      |
| `resource_type` | String    | Resource affected (e.g., `EmailAccount`)     |
| `resource_id`   | UUID      | ID of affected resource                      |
| `details`       | JSONB     | Additional context                           |
| `ip_address`    | String    | Client IP address                            |
| `user_agent`    | String    | Client user agent                            |
| `timestamp`     | Timestamp | When action occurred                         |

**Action Types:**
- `user.login`
- `user.logout`
- `user.delete`
- `email_account.connected`
- `email_account.revoked`
- `email_account.sync_started`
- `email_account.sync_completed`
- `email_account.sync_failed`
- `transaction.created`
- `transaction.updated`
- `transaction.deleted`
- `session.revoked`

**Example Audit Log Entry:**
```json
{
  "id": "audit-001",
  "user_id": "user-123",
  "action": "email_account.connected",
  "resource_type": "EmailAccount",
  "resource_id": "email-acc-456",
  "details": {
    "email_address": "john.doe@gmail.com",
    "scopes_granted": ["gmail.readonly"]
  },
  "ip_address": "203.0.113.42",
  "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
  "timestamp": "2026-02-11T12:00:00Z"
}
```

---

### Audit Log Retention

- **Active logs**: Retained for 90 days in hot storage (PostgreSQL)
- **Archived logs**: After 90 days, moved to cold storage (S3) for 7 years (compliance)
- **User deletion**: Audit logs for deleted users retained for 90 days (fraud prevention), then redacted (user_id replaced with `[DELETED]`)

---

### Alerting on Suspicious Activity

**Automated Alerts:**
1. **Unusual location**: Login from new country → Email alert
2. **Mass token revocation**: >10 tokens revoked in 1 hour → Security team notified
3. **Failed login attempts**: >5 failed attempts in 15 minutes → Rate limit + CAPTCHA
4. **Token leaked**: Refresh token used from >3 different IPs in 1 hour → Revoke token + notify user

---

## Threat Model & Mitigations

### Threat 1: OAuth Token Theft (Database Breach)

**Scenario**: Attacker gains read access to PostgreSQL database.

**Assets at Risk**:
- Encrypted OAuth refresh tokens
- Encrypted DEKs

**Mitigations**:
- ✅ **Envelope encryption**: Tokens encrypted with per-user DEKs; DEKs encrypted with KEK in KMS
- ✅ **KEK never in DB**: Master key stored in AWS KMS (HSM-backed)
- ✅ **No plaintext tokens**: Even DB admin cannot decrypt tokens without KMS access
- ✅ **Audit logs**: All KMS decrypt calls logged (detect unauthorized access)

**Residual Risk**: Low (requires compromise of both DB and KMS IAM credentials)

---

### Threat 2: Session Hijacking (Cookie Theft)

**Scenario**: Attacker steals session cookie via XSS or network interception.

**Assets at Risk**:
- User session (access to dashboard, transactions)

**Mitigations**:
- ✅ **httpOnly cookies**: JavaScript cannot access (XSS protection)
- ✅ **Secure flag**: Cookies only sent over HTTPS (MitM protection)
- ✅ **SameSite=Lax**: CSRF protection
- ✅ **Short expiry**: Sessions expire after 7 days (reduces window)
- ✅ **JTI revocation**: Immediate session invalidation on logout/delete

**Residual Risk**: Medium (XSS vulnerabilities or compromised HTTPS could still leak cookies)

**Additional Mitigation (V2)**: Bind session to IP address or fingerprint (trade-off: breaks mobile users switching networks)

---

### Threat 3: Phishing (User Social Engineering)

**Scenario**: Attacker tricks user into granting OAuth access to malicious app.

**Assets at Risk**:
- Gmail access (via phishing app's OAuth tokens)

**Mitigations**:
- ✅ **Google's OAuth UI**: Shows app name, scopes, and developer info (user can verify legitimacy)
- ✅ **Domain verification**: Spendi domain verified with Google (shows checkmark)
- ✅ **User education**: In-app explanations of what access means
- ✅ **Revocation instructions**: Clear steps to revoke access if suspicious

**Residual Risk**: Medium (depends on user awareness)

**Additional Mitigation (V2)**: Email user after OAuth grant with revocation link ("Was this you?")

---

### Threat 4: Insider Threat (Malicious Employee)

**Scenario**: Spendi employee with DB access attempts to steal user data.

**Assets at Risk**:
- Encrypted OAuth tokens
- Transaction data (plaintext in DB)

**Mitigations**:
- ✅ **Least privilege**: Developers have read-only DB access in production
- ✅ **Encrypted tokens**: Even with DB access, cannot decrypt tokens without KMS permissions
- ✅ **Audit logs**: All DB queries logged with employee ID
- ✅ **Background checks**: Employees vetted before granting production access
- ✅ **Separation of duties**: No single person has both DB and KMS access

**Residual Risk**: Low (transaction data still visible in plaintext; consider field-level encryption for V2)

**Additional Mitigation (V2)**: Encrypt sensitive transaction fields (merchant, amount) with user-specific keys

---

### Threat 5: Dependency Vulnerability (Supply Chain Attack)

**Scenario**: Malicious code in third-party library (e.g., compromised npm package).

**Assets at Risk**:
- All data (if backdoor in library)

**Mitigations**:
- ✅ **Dependency scanning**: Snyk/Dependabot alerts on known vulnerabilities
- ✅ **Lock files**: `package-lock.json`, `poetry.lock` ensure reproducible builds
- ✅ **Code review**: Major dependency updates reviewed by team
- ✅ **Minimal dependencies**: Only use well-maintained, popular libraries
- ✅ **Content Security Policy (CSP)**: Restrict script sources (prevent XSS from compromised CDN)

**Residual Risk**: Medium (zero-day vulnerabilities in dependencies)

**Additional Mitigation (V2)**: Subresource Integrity (SRI) for CDN assets

---

### Threat 6: API Abuse (Gmail API Quota Exhaustion)

**Scenario**: Attacker spams requests to exhaust Spendi's Gmail API quota, causing service disruption.

**Assets at Risk**:
- Service availability (cannot sync emails for legitimate users)

**Mitigations**:
- ✅ **Rate limiting**: Max 10 API requests per user per minute
- ✅ **CAPTCHA**: Require CAPTCHA after 5 failed requests
- ✅ **IP-based limits**: Max 100 requests per IP per hour
- ✅ **Monitoring**: Alert if API usage spikes >50% above baseline

**Residual Risk**: Low (distributed attack could still exhaust quota)

**Additional Mitigation (V2)**: Request higher quota from Google preemptively

---

## What is NEVER Stored

Spendi adheres to strict data minimization principles:

### ❌ Never Stored:

1. **Passwords**: Spendi uses OAuth exclusively; no password storage
2. **Full email content**: Only extracted transaction fields (merchant, amount, date) stored; email body discarded
3. **Email attachments**: Never downloaded or stored
4. **Full credit card numbers**: Only last 4 digits stored
5. **CVV/PIN/Security codes**: Never requested or stored
6. **Social Security Numbers**: Never requested or stored
7. **Bank account credentials**: No Plaid integration; no bank login credentials
8. **Unencrypted OAuth tokens**: Tokens always encrypted at rest
9. **Plaintext passwords or secrets in logs**: All logs sanitized (no credentials)
10. **User location data**: Not tracked (unless explicitly provided in transaction)

### ✅ What IS Stored (Minimal Data):

1. **User profile**: Email, name (from OAuth)
2. **Transaction metadata**: Merchant, amount, date, card last 4
3. **Encrypted OAuth tokens**: Refresh tokens for Gmail API (encrypted)
4. **Session tokens**: JTI in Redis (for revocation)
5. **Audit logs**: User actions (login, revoke, delete)

---

## FastAPI Implementation Guide

### 1. OAuth Routes (Backend)

**File: `backend/app/auth/routes.py`**

```python
from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
import jwt
import os
from datetime import datetime, timedelta
from app.db.session import get_db
from app.db.models import User, EmailAccount
from app.auth.encryption import encrypt_token, decrypt_token
from app.auth.audit import log_audit_event

router = APIRouter(prefix="/auth/google", tags=["auth"])

# OAuth client setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_OAUTH_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_OAUTH_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# ============================================================================
# Step 1: User Authentication (Login)
# ============================================================================

@router.get("/authorize")
async def google_authorize(request: Request):
    """Redirect to Google OAuth consent screen for user authentication."""
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def google_callback(request: Request, response: Response, db=Depends(get_db)):
    """Handle OAuth callback after user grants consent."""
    try:
        # Exchange authorization code for tokens
        token = await oauth.google.authorize_access_token(request)

        # Verify ID token signature
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        email = user_info['email']
        oauth_subject_id = user_info['sub']  # Stable Google user ID
        display_name = user_info.get('name')

        # Create or update user
        user = db.query(User).filter(
            User.oauth_provider == 'google',
            User.oauth_subject_id == oauth_subject_id
        ).first()

        if not user:
            user = User(
                email=email,
                oauth_provider='google',
                oauth_subject_id=oauth_subject_id,
                display_name=display_name
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Generate session token (JWT)
        session_payload = {
            "sub": str(user.id),
            "email": user.email,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(days=7),
            "jti": f"session-{user.id}-{int(datetime.utcnow().timestamp())}"
        }
        session_token = jwt.encode(session_payload, SECRET_KEY, algorithm="HS256")

        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=True,  # HTTPS only
            samesite="Lax",
            max_age=604800  # 7 days
        )

        # Log audit event
        log_audit_event(
            user_id=user.id,
            action="user.login",
            resource_type="User",
            resource_id=user.id,
            ip_address=request.client.host,
            user_agent=request.headers.get('User-Agent')
        )

        # Redirect to frontend dashboard
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth failed: {str(e)}")


# ============================================================================
# Step 2: Gmail Access (Separate Consent)
# ============================================================================

@router.get("/authorize-gmail")
async def google_authorize_gmail(request: Request):
    """Redirect to Google OAuth consent screen for Gmail access."""
    redirect_uri = request.url_for('google_gmail_callback')
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        scope='https://www.googleapis.com/auth/gmail.readonly',
        access_type='offline',  # Get refresh token
        prompt='consent'  # Force consent screen (to get refresh token)
    )


@router.get("/gmail-callback")
async def google_gmail_callback(request: Request, db=Depends(get_db)):
    """Handle Gmail OAuth callback."""
    try:
        # Get current user from session
        user = get_current_user(request, db)

        # Exchange authorization code for tokens
        token = await oauth.google.authorize_access_token(request)
        access_token = token['access_token']
        refresh_token = token.get('refresh_token')
        expires_at = datetime.utcnow() + timedelta(seconds=token['expires_in'])

        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="No refresh token received. Try disconnecting and reconnecting."
            )

        # Encrypt tokens using envelope encryption
        encrypted_access = encrypt_token(access_token, user.id)
        encrypted_refresh = encrypt_token(refresh_token, user.id)

        # Create or update EmailAccount
        email_account = db.query(EmailAccount).filter(
            EmailAccount.user_id == user.id,
            EmailAccount.email_address == user.email
        ).first()

        if not email_account:
            email_account = EmailAccount(
                user_id=user.id,
                provider='gmail',
                email_address=user.email,
                oauth_access_token=encrypted_access['ciphertext'],
                oauth_refresh_token=encrypted_refresh['ciphertext'],
                encryption_key=encrypted_refresh['encrypted_dek'],
                encryption_iv=encrypted_refresh['iv'],
                oauth_token_expires_at=expires_at,
                sync_enabled=True
            )
            db.add(email_account)
        else:
            email_account.oauth_access_token = encrypted_access['ciphertext']
            email_account.oauth_refresh_token = encrypted_refresh['ciphertext']
            email_account.encryption_key = encrypted_refresh['encrypted_dek']
            email_account.encryption_iv = encrypted_refresh['iv']
            email_account.oauth_token_expires_at = expires_at
            email_account.sync_enabled = True

        db.commit()

        # Log audit event
        log_audit_event(
            user_id=user.id,
            action="email_account.connected",
            resource_type="EmailAccount",
            resource_id=email_account.id,
            details={"email_address": user.email},
            ip_address=request.client.host,
            user_agent=request.headers.get('User-Agent')
        )

        # Trigger initial email sync (background job)
        from app.jobs.email_sync import trigger_email_sync
        trigger_email_sync.delay(email_account.id)

        # Redirect to dashboard with success message
        return RedirectResponse(url=f"{FRONTEND_URL}/dashboard?gmail_connected=true")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gmail OAuth failed: {str(e)}")


# ============================================================================
# Revoke Gmail Access
# ============================================================================

@router.post("/revoke-gmail/{email_account_id}")
async def revoke_gmail_access(email_account_id: str, request: Request, db=Depends(get_db)):
    """Revoke Gmail API access."""
    user = get_current_user(request, db)

    # Verify user owns this email account
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id,
        EmailAccount.user_id == user.id
    ).first()

    if not email_account:
        raise HTTPException(status_code=404, detail="Email account not found")

    # Decrypt refresh token
    refresh_token = decrypt_token(
        email_account.oauth_refresh_token,
        email_account.encryption_key,
        email_account.encryption_iv,
        user.id
    )

    # Revoke token at Google
    import requests
    revoke_response = requests.post(
        'https://oauth2.googleapis.com/revoke',
        data={'token': refresh_token},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )

    # Delete encrypted tokens from DB
    email_account.oauth_access_token = None
    email_account.oauth_refresh_token = None
    email_account.encryption_key = None
    email_account.encryption_iv = None
    email_account.sync_enabled = False
    db.commit()

    # Log audit event
    log_audit_event(
        user_id=user.id,
        action="email_account.revoked",
        resource_type="EmailAccount",
        resource_id=email_account.id,
        ip_address=request.client.host,
        user_agent=request.headers.get('User-Agent')
    )

    return {"message": "Gmail access revoked successfully"}


# ============================================================================
# Helper: Get Current User from Session
# ============================================================================

def get_current_user(request: Request, db) -> User:
    """Extract user from session token."""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = db.query(User).filter(User.id == payload['sub']).first()
        if not user or user.deleted_at:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

### 2. Envelope Encryption Module

**File: `backend/app/auth/encryption.py`**

```python
import os
import boto3
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# AWS KMS client
kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
KEK_KEY_ID = os.getenv('AWS_KMS_KEY_ID')  # ARN of master key


def encrypt_token(plaintext: str, user_id: str) -> dict:
    """
    Encrypt a token using envelope encryption.

    Returns:
        {
            'ciphertext': base64-encoded encrypted token,
            'encrypted_dek': base64-encoded encrypted DEK,
            'iv': base64-encoded initialization vector
        }
    """
    # Generate DEK (Data Encryption Key)
    dek = os.urandom(32)  # 256-bit key

    # Encrypt plaintext with DEK (AES-256-GCM)
    iv = os.urandom(12)  # 96-bit IV for GCM
    cipher = Cipher(
        algorithms.AES(dek),
        modes.GCM(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode()) + encryptor.finalize()
    auth_tag = encryptor.tag

    # Encrypt DEK with KEK (AWS KMS)
    kms_response = kms_client.encrypt(
        KeyId=KEK_KEY_ID,
        Plaintext=dek,
        EncryptionContext={
            'purpose': 'oauth-token-encryption',
            'user_id': user_id
        }
    )
    encrypted_dek = kms_response['CiphertextBlob']

    return {
        'ciphertext': base64.b64encode(ciphertext + auth_tag).decode(),
        'encrypted_dek': base64.b64encode(encrypted_dek).decode(),
        'iv': base64.b64encode(iv).decode()
    }


def decrypt_token(ciphertext_b64: str, encrypted_dek_b64: str, iv_b64: str, user_id: str) -> str:
    """
    Decrypt a token using envelope encryption.

    Args:
        ciphertext_b64: Base64-encoded encrypted token
        encrypted_dek_b64: Base64-encoded encrypted DEK
        iv_b64: Base64-encoded IV
        user_id: User ID (for encryption context)

    Returns:
        Decrypted plaintext token
    """
    # Decode from base64
    ciphertext_and_tag = base64.b64decode(ciphertext_b64)
    encrypted_dek = base64.b64decode(encrypted_dek_b64)
    iv = base64.b64decode(iv_b64)

    # Split ciphertext and auth tag (last 16 bytes)
    ciphertext = ciphertext_and_tag[:-16]
    auth_tag = ciphertext_and_tag[-16:]

    # Decrypt DEK with KEK (AWS KMS)
    kms_response = kms_client.decrypt(
        CiphertextBlob=encrypted_dek,
        EncryptionContext={
            'purpose': 'oauth-token-encryption',
            'user_id': user_id
        }
    )
    dek = kms_response['Plaintext']

    # Decrypt ciphertext with DEK (AES-256-GCM)
    cipher = Cipher(
        algorithms.AES(dek),
        modes.GCM(iv, auth_tag),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    return plaintext.decode()
```

---

### 3. Audit Logging Module

**File: `backend/app/auth/audit.py`**

```python
from app.db.session import get_db
from app.db.models import AuditLog
from datetime import datetime
import uuid


def log_audit_event(
    user_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None
):
    """Log a security-sensitive event to the audit trail."""
    db = next(get_db())

    audit_log = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.utcnow()
    )

    db.add(audit_log)
    db.commit()
```

---

### 4. Dependency: Session Validation Middleware

**File: `backend/app/auth/middleware.py`**

```python
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer
import jwt
from app.db.session import get_db
from app.db.models import User
import os

SECRET_KEY = os.getenv('JWT_SECRET_KEY')
security = HTTPBearer()


async def get_current_user(request: Request) -> User:
    """Extract and validate current user from session token."""
    token = request.cookies.get('session_token')
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload['sub']

        db = next(get_db())
        user = db.query(User).filter(User.id == user_id).first()

        if not user or user.deleted_at:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid session token")
```

---

### 5. Environment Variables

**File: `backend/.env.example`**

```bash
# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# JWT Session Secret
JWT_SECRET_KEY=your-256-bit-secret-key-here

# AWS KMS (for token encryption)
AWS_REGION=us-east-1
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789012:key/your-key-id
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Frontend URL (for OAuth redirects)
FRONTEND_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/spendi

# Redis (for session revocation)
REDIS_URL=redis://localhost:6379/0
```

---

## Security Checklist

### Pre-Launch Checklist

- [ ] **OAuth Configuration**
  - [ ] Google OAuth credentials configured (client ID + secret)
  - [ ] Redirect URIs whitelisted in Google Console
  - [ ] Domain ownership verified with Google
  - [ ] OAuth consent screen reviewed (accurate branding, privacy policy link)

- [ ] **Token Encryption**
  - [ ] AWS KMS key created and IAM permissions configured
  - [ ] Envelope encryption tested (encrypt + decrypt flow)
  - [ ] KEK rotation policy configured (annual)
  - [ ] Encryption context validated (purpose, user_id)

- [ ] **Session Management**
  - [ ] JWT secret key is 256-bit random (not hardcoded)
  - [ ] Session cookies have `httpOnly`, `Secure`, `SameSite=Lax`
  - [ ] Session expiry configured (7 days)
  - [ ] JTI blacklist implemented (Redis)

- [ ] **HTTPS/TLS**
  - [ ] TLS 1.3 enabled (or TLS 1.2 minimum)
  - [ ] Valid SSL certificate installed
  - [ ] HTTP redirects to HTTPS
  - [ ] HSTS header configured (`Strict-Transport-Security`)

- [ ] **Audit Logging**
  - [ ] All auth events logged (login, logout, revoke, delete)
  - [ ] Audit logs immutable (append-only table)
  - [ ] Sensitive data redacted from logs (no tokens, passwords)
  - [ ] Log retention policy configured (90 days hot + 7 years cold)

- [ ] **Threat Mitigations**
  - [ ] Rate limiting implemented (per user, per IP)
  - [ ] CAPTCHA on failed login attempts (>5 failures)
  - [ ] CSRF protection enabled (SameSite cookies + CSRF tokens for state-changing requests)
  - [ ] XSS protection (Content Security Policy header)
  - [ ] SQL injection prevention (parameterized queries only)

- [ ] **Monitoring & Alerts**
  - [ ] Failed login alerts (>5 failures in 15 minutes)
  - [ ] Unusual location alerts (new country login)
  - [ ] KMS decrypt call monitoring (spike detection)
  - [ ] API quota monitoring (Gmail API usage)

- [ ] **User Controls**
  - [ ] Revoke Gmail access endpoint tested
  - [ ] Delete account flow tested (soft delete + 30-day grace period)
  - [ ] Data export endpoint tested (GDPR compliance)
  - [ ] Privacy policy published and linked in app

---

## Next Steps

1. **Implement OAuth Flows** (FastAPI routes above)
2. **Set Up AWS KMS** (create KEK, configure IAM policies)
3. **Test Encryption** (unit tests for encrypt/decrypt)
4. **Configure Google OAuth Console** (add redirect URIs, consent screen)
5. **Deploy to Staging** (test full OAuth flow end-to-end)
6. **Security Audit** (penetration testing, code review)
7. **Launch** 🚀

---

## Document History

| Version | Date       | Author   | Changes                             |
|---------|------------|----------|-------------------------------------|
| 1.0     | 2026-02-11 | Security | Initial auth & security design      |

---

**Questions? Contact**: security@spendi.app