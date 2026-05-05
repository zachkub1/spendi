# Phase 1 Testing Guide

## Prerequisites

✅ PostgreSQL running (port 5432)
✅ Redis running (port 6379)
✅ Database migrations applied
✅ Backend imports successfully

## Setup Environment Variables

### Backend (.env)

Create `/Users/zach/Desktop/meMoney/backend/.env` with:

```bash
# Copy from .env.example and fill in values
ENVIRONMENT=development
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

DATABASE_URL=postgresql://postgres:postgres@localhost:5432/spendi
REDIS_URL=redis://localhost:6379/0

# Generate a secure key for production
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Get from Google Cloud Console (https://console.cloud.google.com/)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
ENCRYPTION_MASTER_KEY=6c9f697d67f83a90659fdcf1c76ee40acbcc6ffcfd862cf11931a374a439f7f7
```

### Frontend (.env.local)

Ensure `/Users/zach/Desktop/meMoney/frontend/.env.local` has:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Gmail API** and **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs:
   - `http://localhost:8000/auth/callback`
   - `http://localhost:3000/auth/callback`
7. Copy **Client ID** and **Client Secret** to backend `.env`

## Start Services

### Terminal 1: Backend Server

```bash
cd /Users/zach/Desktop/meMoney/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Terminal 2: Celery Worker (for Week 3 sync tasks)

```bash
cd /Users/zach/Desktop/meMoney/backend
source venv/bin/activate
celery -A jobs.celery_app worker --loglevel=info
```

### Terminal 3: Frontend Development Server

```bash
cd /Users/zach/Desktop/meMoney/frontend
npm run dev
```

Expected output:
```
  ▲ Next.js 14.1.0
  - Local:        http://localhost:3000
```

## Testing Checklist

### Week 1: OAuth Authentication

1. **Access Homepage**
   - Navigate to: http://localhost:3000
   - Should redirect to `/login`

2. **Login Flow**
   - Click "Sign in with Google"
   - Should redirect to Google OAuth consent screen
   - Grant permissions
   - Should redirect back to `/dashboard`

3. **Verify Session**
   - Check localStorage for `spendi_auth_token`
   - UserMenu should show your email in top-right
   - Refresh page → should stay authenticated

4. **Protected Routes**
   - Try accessing http://localhost:3000/dashboard without auth
   - Should redirect to `/login`

5. **Logout**
   - Click UserMenu → Logout
   - Should redirect to `/login`
   - localStorage token should be cleared

6. **API Endpoints**
   - Visit: http://localhost:8000/docs (FastAPI Swagger UI)
   - Test `GET /auth/me` with Bearer token

### Week 2: Gmail Integration

1. **Connect Gmail Account**
   - Login to app
   - Navigate to http://localhost:3000/email
   - Click "Connect Gmail Account"
   - Should request Gmail permissions (gmail.readonly scope)
   - Grant access
   - Account should appear in connected accounts list

2. **Verify Encryption**
   ```bash
   # Check database - tokens should be encrypted
   docker exec -it spendi-db psql -U postgres -d spendi \
     -c "SELECT email_address, substring(oauth_access_token, 1, 20) FROM email_accounts;"
   ```
   - Should see base64-encoded encrypted data, NOT plaintext tokens

3. **Test Gmail API**
   - Backend: http://localhost:8000/docs
   - Try `GET /email/messages?account_id={id}`
   - Should return list of Gmail message IDs

4. **Disconnect Account**
   - Click "Disconnect" button
   - Account should be removed
   - Database record should be deleted

### Week 3: Email Parsing

1. **Sync Emails**
   - Connect Gmail account (must have financial emails from Chase/Amex/Venmo/Zelle)
   - Click "Sync Emails" button
   - Watch Celery worker logs for parsing activity
   - Wait ~5 seconds for sync to complete

2. **View Parsed Transactions**
   - Transaction list should appear below email accounts
   - Each transaction should show:
     - Merchant name
     - Amount
     - Transaction date
     - Card last 4 digits (if applicable)
     - Confidence score

3. **Verify Database**
   ```bash
   # Check RawEmail records
   docker exec -it spendi-db psql -U postgres -d spendi \
     -c "SELECT message_id, subject, parsing_status, parser_used FROM raw_emails LIMIT 5;"

   # Check ParsedTransaction records
   docker exec -it spendi-db psql -U postgres -d spendi \
     -c "SELECT merchant_name, amount, transaction_date, card_last_four, confidence_score FROM parsed_transactions LIMIT 5;"
   ```

4. **Idempotency Test**
   - Click "Sync Emails" again
   - Should NOT create duplicate transactions
   - Check raw_emails table - message_id should be unique

5. **Parser Coverage**
   - Test with emails from each provider:
     - Chase: Transaction notification emails
     - Amex: Charge notification emails
     - Venmo: Payment notification emails
     - Zelle: Transfer notification emails

## API Endpoints Reference

### Authentication
- `GET /auth/login` - Get Google OAuth URL
- `GET /auth/callback?code=xxx` - OAuth callback
- `GET /auth/me` - Get current user (requires auth)
- `POST /auth/logout` - Logout (creates audit log)

### Email Accounts
- `POST /email/connect` - Connect Gmail account
- `GET /email/accounts` - List connected accounts
- `DELETE /email/accounts/{id}` - Disconnect account
- `GET /email/messages?account_id={id}` - List Gmail messages (testing)

### Email Sync (Week 3)
- `POST /email/sync/{account_id}` - Trigger manual sync
- `GET /email/transactions?account_id={id}&limit=50` - List parsed transactions

### System
- `GET /health` - Health check
- `GET /` - API info
- `GET /docs` - Swagger UI

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `docker ps | grep postgres`
- Check Redis is running: `docker ps | grep redis`
- Verify migrations: `alembic current`
- Check logs for import errors

### Frontend won't build
- Clear Next.js cache: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`
- Check TypeScript errors: `npm run build`

### OAuth not working
- Verify Google Cloud Console redirect URIs match exactly
- Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in `.env`
- Ensure CORS is configured correctly (FRONTEND_URL in backend config)

### Gmail sync not working
- Check Celery worker is running
- Verify ENCRYPTION_MASTER_KEY is set
- Check Gmail API is enabled in Google Cloud Console
- Ensure oauth_refresh_token was granted (requires `prompt=consent`)

### Database issues
- Reset database: `docker-compose down -v && docker-compose up -d`
- Rerun migrations: `alembic downgrade base && alembic upgrade head`

## Success Criteria

✅ User can sign in with Google OAuth
✅ Protected routes work correctly
✅ Session persists across page refreshes
✅ User can connect Gmail account
✅ OAuth tokens are encrypted in database
✅ Manual email sync discovers financial emails
✅ Transactions are parsed from 4 providers
✅ Parsed transactions display in frontend
✅ No duplicate processing (idempotent)
✅ Frontend builds without errors
✅ Backend starts without errors

## Next Steps (Phase 2)

After Phase 1 is verified:
- Transaction reconciliation (match email transactions to bank imports)
- Rewards optimization tracking
- Budget insights and forecasting
- Scheduled background syncs (Celery Beat)
- ML-based merchant categorization
