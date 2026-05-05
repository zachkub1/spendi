# Product Requirements Document: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Product & Engineering

---

## Executive Summary

Spendi is a privacy-first personal finance tracker that automatically ingests financial transaction data from email, normalizes it into a unified ledger, and provides explainable insights into spending, reimbursements, and credit card rewards optimization. Unlike traditional finance apps that require bank account linking, Spendi operates read-only by parsing transaction notifications from email, ensuring users maintain full control of their financial credentials.

**Target Users**: Individuals who:
- Manage multiple credit cards and payment methods
- Receive partial reimbursements (business expenses, shared costs, family reimbursements)
- Want to optimize credit card rewards without manual tracking
- Prioritize financial privacy and data ownership

**Core Value Proposition**:
- Automatic transaction ingestion from email (no bank linking required)
- Unified ledger across all payment methods
- Transparent reimbursement tracking with partial offset support
- Rewards optimization per card
- Privacy-first: your data stays yours, no data sales

---

## Problem Statement

### User Pain Points
1. **Fragmented Transaction View**: Users have transactions across multiple credit cards, debit cards, and P2P apps (Zelle, Venmo, Cash App) with no unified view
2. **Manual Reimbursement Tracking**: No easy way to track which personal purchases were partially or fully reimbursed
3. **Rewards Suboptimization**: Users don't know which card to use for which category to maximize rewards
4. **Privacy Concerns**: Traditional finance apps require bank account linking and sell user data
5. **Manual Entry Overhead**: Spreadsheet-based tracking is tedious and error-prone
6. **Lack of Explainability**: Existing apps use black-box categorization without showing reasoning

### Current Alternatives
- **Mint/Personal Capital**: Require bank linking, sell data, lack reimbursement tracking
- **Spreadsheets**: Manual entry, no automation, error-prone
- **Credit Card Apps**: Siloed per card, no cross-card view or rewards optimization
- **YNAB**: Requires manual transaction entry, focused on budgeting not tracking

---

## Goals & Success Metrics

### Business Goals
1. Launch MVP with 100 beta users within 3 months
2. Achieve 80% transaction auto-ingestion accuracy (parsed correctly from email)
3. Demonstrate value: users save avg 30 minutes/week vs manual tracking
4. Build trust: zero data breaches, clear privacy policy

### User Goals
1. See all transactions across payment methods in one place
2. Track reimbursements and understand true out-of-pocket spending
3. Optimize credit card rewards without manual calculation
4. Maintain financial privacy and data ownership

### Success Metrics (MVP)
- **Engagement**: 70% of users return weekly to review transactions
- **Accuracy**: 85% of email-parsed transactions require no manual correction
- **Coverage**: Support 80% of users' credit cards (Amex, Chase, Citi, Discover, Capital One)
- **Trust**: 90% of users rate privacy protections as "excellent" or "good"
- **Utility**: Users track avg 5+ payment methods (cards, P2P apps)

---

## Functional Requirements

### FR-1: Email Ingestion & Transaction Parsing

**FR-1.1: Gmail API Integration**
- Users authorize read-only Gmail API access via OAuth 2.0
- App polls Gmail for new emails from known financial senders (daily/hourly)
- Supported senders: credit card issuers, banks, Zelle, Venmo, Cash App, PayPal
- Email parsing extracts: merchant, amount, date, card last 4 digits, transaction type (purchase/refund/payment)

**FR-1.2: Multi-Format Email Support**
- Parse plain text and HTML emails
- Handle common formats: "You spent $X at Merchant" / "Transaction approved: $X" / "Zelle payment to Name"
- Extract transaction IDs for duplicate detection

**FR-1.3: Duplicate Detection**
- Detect duplicate emails for same transaction (e.g., initial authorization + final settlement)
- Use transaction ID, amount, merchant, date, and card last 4 as match criteria
- Auto-deduplicate or flag for user review

**FR-1.4: Supported Payment Methods (MVP)**
- **Credit Cards**: Amex, Chase, Citi, Discover, Capital One, Bank of America
- **Debit Cards**: All major banks that send email notifications
- **P2P Apps**: Zelle, Venmo, Cash App (transaction confirmations)
- **Out of Scope (V2)**: Bank transfers, checks, wire transfers, crypto

**FR-1.5: Manual Entry Fallback**
- If email parsing fails or no email received, users can manually add transactions
- Manual entry form: date, merchant, amount, payment method, category (optional), notes

### FR-2: Unified Transaction Ledger

**FR-2.1: Normalized Transaction Model**
Each transaction record includes:
- **ID**: Unique identifier
- **Date**: Transaction date (not email receipt date)
- **Merchant**: Normalized merchant name (e.g., "AMZN*abc123" → "Amazon")
- **Amount**: Decimal precision (e.g., $12.34)
- **Payment Method**: Card name or P2P app (e.g., "Chase Sapphire Reserve", "Venmo")
- **Card Last 4**: If applicable
- **Category**: Auto-assigned or user-override (e.g., Dining, Groceries, Travel)
- **Transaction Type**: Purchase, Refund, Payment, Transfer
- **Status**: Pending, Settled, Reimbursed (partial/full)
- **Reimbursement Amount**: If applicable (e.g., $50 of $100 reimbursed)
- **Notes**: User-added notes
- **Source**: Email or Manual Entry
- **Confidence Score**: If auto-categorized (0-100%)

**FR-2.2: Merchant Normalization**
- Parse raw merchant strings (e.g., "SQ *COFFEE SHOP NYC", "AMZN*Prime Video")
- Map to clean names (e.g., "Square - Coffee Shop", "Amazon Prime Video")
- Learn from user corrections (e.g., if user renames "SQ *X" to "Joe's Cafe", apply to future)

**FR-2.3: Multi-Currency Support (V2)**
- MVP: USD only
- V2: Support multiple currencies with exchange rate tracking

### FR-3: Reimbursement Tracking

**FR-3.1: Reimbursement Assignment**
- Users can mark a transaction as "Reimbursed" (full or partial)
- Specify reimbursement amount (e.g., $50 of $100 transaction)
- Specify reimbursement source (e.g., "Work reimbursement", "Friend: John", "Zelle from Sarah")
- Specify reimbursement date

**FR-3.2: Reimbursement Matching (V2)**
- Automatically match incoming Zelle/Venmo/Cash App receipts to previous purchases
- Suggest matches based on amount and date proximity
- User confirms or overrides matches

**FR-3.3: Net Spending Calculation**
- Display gross spending vs net spending (after reimbursements)
- Show per category: "Dining: $500 gross, $150 reimbursed, $350 net"
- Timeline view: show original purchase and reimbursement side-by-side

**FR-3.4: Reimbursement Reports**
- Generate reports: "Total reimbursed this month: $X across Y transactions"
- Export reimbursement log for tax/accounting purposes

### FR-4: Credit Card Rewards Tracking

**FR-4.1: Card Profile Setup**
- Users add credit cards with reward structure:
  - Card name (e.g., "Chase Sapphire Reserve")
  - Last 4 digits
  - Reward rates per category (e.g., 3% dining, 1% other)
  - Annual fee, signup bonus, benefits

**FR-4.2: Rewards Calculation**
- For each transaction, calculate points/cash back earned based on card and category
- Display per transaction: "Earned 300 points (3% on $100 dining)"
- Aggregate: "Total points earned this month: 5,420"

**FR-4.3: Rewards Optimization**
- Suggest better card for each transaction: "You used Card A (1% back); Card B offers 3% for dining"
- Monthly report: "Potential missed rewards: $45 if optimal card used"
- Category-specific recommendations: "Use Card X for groceries, Card Y for gas"

**FR-4.4: Points Value Tracking (V2)**
- Track point redemption value (e.g., Chase points worth 1.5¢ each if redeemed for travel)
- Calculate true rewards earned in dollar terms

### FR-5: Transaction Viewing & Management

**FR-5.1: Transaction List View**
- Default view: reverse chronological list of all transactions
- Columns: Date, Merchant, Amount, Payment Method, Category, Status, Reimbursement
- Pagination (50 transactions per page)
- Infinite scroll option

**FR-5.2: Filtering & Search**
- Filter by: Date range, Payment method, Category, Merchant, Status (pending/settled/reimbursed)
- Search by: Merchant name, amount, notes
- Saved filters (e.g., "Unreimbursed work expenses")

**FR-5.3: Sorting**
- Sort by: Date, Amount, Merchant, Category
- Ascending/descending

**FR-5.4: Transaction Detail View**
- Click transaction to see full details:
  - Original email snippet (if sourced from email)
  - Edit capability (merchant, category, notes, reimbursement)
  - Delete option (soft delete with audit trail)
  - Related transactions (e.g., original purchase + reimbursement)

**FR-5.5: Bulk Operations (V2)**
- Select multiple transactions
- Bulk categorize, bulk mark as reimbursed, bulk export

### FR-6: Categorization & Tagging

**FR-6.1: Auto-Categorization**
- Use rule-based logic + ML model to assign categories
- Common categories: Groceries, Dining, Gas, Travel, Entertainment, Shopping, Utilities, Healthcare, Other
- Display confidence score (e.g., "85% confident this is Dining")

**FR-6.2: User Override**
- Users can change category for any transaction
- System learns from overrides (e.g., "Costco" → "Groceries" not "Shopping")

**FR-6.3: Custom Categories (V2)**
- Users can create custom categories (e.g., "Pet Expenses", "Home Improvement")
- Map to standard categories for rewards calculation

**FR-6.4: Tags (V2)**
- Add tags to transactions (e.g., "vacation", "wedding expenses", "tax deductible")
- Filter by tags

### FR-7: Dashboards & Insights

**FR-7.1: Overview Dashboard**
- Current month spending: Total, by category (pie chart)
- Top merchants this month
- Recent transactions (last 10)
- Pending reimbursements total
- Rewards earned this month (per card)

**FR-7.2: Spending Trends (V2)**
- Month-over-month spending by category (line chart)
- Seasonal trends (e.g., "You spend 30% more on dining in summer")
- Anomaly detection (e.g., "This month's grocery spending is 2x average")

**FR-7.3: Reimbursement Dashboard**
- Pending reimbursements (awaiting payment)
- Reimbursement history (last 3 months)
- Top reimbursement sources (e.g., "Work: 60%, Friends: 40%")

**FR-7.4: Rewards Dashboard**
- Total rewards earned (per card, all-time)
- Monthly rewards trend
- Optimization opportunities (how much left on the table)
- Upcoming annual fees / renewal dates

**FR-7.5: Explainability**
- Every insight links back to underlying transactions
- Example: "Dining spending up 20%" → click to see all dining transactions
- No black-box recommendations without data provenance

### FR-8: Data Export & Portability

**FR-8.1: Transaction Export**
- Export all transactions to CSV / Excel
- Columns: Date, Merchant, Amount, Payment Method, Category, Status, Reimbursement, Notes
- Date range selection

**FR-8.2: Full Data Export (GDPR Compliance)**
- Users can download all data (JSON format)
- Includes transactions, payment methods, settings, audit logs

**FR-8.3: Import (V2)**
- Import transactions from CSV (for historical data or migration from other apps)

### FR-9: User Account & Settings

**FR-9.1: OAuth 2.0 Authentication**
- Sign up / log in via Google OAuth
- No password storage (delegated auth)

**FR-9.2: Payment Method Management**
- Add/edit/remove credit cards (name, last 4, reward structure)
- Add/edit/remove P2P apps (linked account names)
- Deactivate payment methods (hide from filters but keep transaction history)

**FR-9.3: Email Sync Settings**
- Configure sync frequency (hourly, daily, manual only)
- Whitelist/blacklist email senders
- Pause sync temporarily

**FR-9.4: Privacy Settings**
- View OAuth permissions granted
- Revoke Gmail API access
- Delete account and all data

**FR-9.5: Notification Preferences (V2)**
- Email notifications for: New transactions detected, Reimbursement reminders, Monthly summary
- Push notifications (if mobile app in future)

### FR-10: Read-Only Guarantee

**FR-10.1: No Transaction Initiation**
- App CANNOT initiate payments, transfers, or purchases
- App CANNOT modify transactions at financial institutions
- App ONLY reads email for transaction data

**FR-10.2: No Bank Account Linking**
- App does NOT use Plaid or direct bank API integration
- No credential storage for banking institutions
- Users remain in full control of financial account access

---

## Non-Functional Requirements

### NFR-1: Performance

**NFR-1.1: Response Time**
- Page load: < 2 seconds
- Transaction list render (50 items): < 500ms
- Search results: < 1 second
- Email sync job: process 100 emails in < 30 seconds

**NFR-1.2: Scalability**
- Support 10,000 users (MVP)
- Support 1M transactions across all users
- Background jobs scale horizontally (Celery workers)

**NFR-1.3: Uptime**
- 99% uptime (MVP)
- 99.9% uptime (V2)

### NFR-2: Security

**NFR-2.1: Authentication**
- OAuth 2.0 only (no username/password)
- Session tokens expire after 7 days of inactivity
- HTTPS everywhere (no HTTP)

**NFR-2.2: Data Encryption**
- **At rest**: All OAuth tokens encrypted using envelope encryption (AES-256)
- **In transit**: TLS 1.3 for all API calls
- **Database**: PostgreSQL with encryption enabled

**NFR-2.3: Credential Storage**
- OAuth refresh tokens encrypted with per-user keys
- Keys stored in secure vault (AWS KMS, GCP Secret Manager)
- No plaintext credentials in logs or error messages

**NFR-2.4: Access Control**
- Users can ONLY access their own data (enforced at DB query level)
- Admin dashboard requires 2FA
- API endpoints validate user ownership before returning data

**NFR-2.5: Compliance**
- **GDPR**: Right to access, right to delete, data portability
- **CCPA**: Do not sell user data (explicit policy)
- **PCI DSS**: Not applicable (no card storage, no payment processing)

### NFR-3: Privacy Guarantees

**NFR-3.1: No Data Sales**
- Architecture prohibits bulk data export for third parties
- No advertising integrations
- No data sharing with affiliates or partners
- Revenue model: subscription-based (freemium or paid tiers), not data monetization

**NFR-3.2: Minimal Data Retention**
- Only store data necessary for functionality
- Email content NOT stored (only extracted transaction fields)
- Audit logs retained for 90 days, then purged

**NFR-3.3: Transparency**
- Privacy policy in plain English (not legal jargon)
- Changelog for policy updates with user notification
- Open-source libraries used (no proprietary tracking SDKs)

**NFR-3.4: User Control**
- Users can delete account and all data (irrecoverable within 30 days)
- Users can pause email sync at any time
- Users can export data before deletion

### NFR-4: Reliability

**NFR-4.1: Data Integrity**
- All currency calculations use `Decimal` (Python) or `NUMERIC` (Postgres)
- Transaction history is append-only (immutable ledger)
- State changes logged with timestamp and reason

**NFR-4.2: Fault Tolerance**
- Email sync failures logged but don't crash the system
- Failed parsing jobs retried with exponential backoff (max 3 retries)
- Users notified if sync fails for 3+ consecutive attempts

**NFR-4.3: Backup & Recovery**
- Daily automated backups of PostgreSQL database
- Point-in-time recovery (last 7 days)
- Tested restore procedure (quarterly drills)

### NFR-5: Usability

**NFR-5.1: Accessibility**
- WCAG 2.1 Level AA compliance
- Keyboard navigation support
- Screen reader compatible
- High contrast mode

**NFR-5.2: Responsiveness**
- Mobile-first design (works on phones, tablets, desktop)
- Responsive breakpoints: 320px, 768px, 1024px, 1440px

**NFR-5.3: User Onboarding**
- First-time user flow: OAuth → Grant Gmail access → Sync first batch → Tour of features
- Contextual help tooltips for key features
- Sample data for demo accounts

**NFR-5.4: Error Messaging**
- Errors are actionable (e.g., "Sync failed: Gmail access revoked. [Re-authorize]")
- No technical jargon in user-facing messages
- Link to support docs for troubleshooting

### NFR-6: Maintainability

**NFR-6.1: Code Quality**
- 80% unit test coverage (critical paths: 100%)
- Type-safe APIs (Pydantic for backend, Zod for frontend)
- Linting enforced (Black, ESLint/Prettier)

**NFR-6.2: Documentation**
- API documentation auto-generated (FastAPI/OpenAPI)
- Architecture decision records (ADRs) for major choices
- README per module with setup instructions

**NFR-6.3: Observability**
- Structured logging (JSON) with correlation IDs
- Application metrics (request rate, error rate, latency)
- Healthcheck endpoints for uptime monitoring

---

## Out of Scope (Not MVP)

### Out of Scope (Explicitly NOT Doing)
1. **Bank Account Linking**: No Plaid integration, no direct bank API access
2. **Investment Tracking**: No stocks, bonds, crypto, retirement accounts (MVP)
3. **Bill Payment**: No transaction initiation, no autopay
4. **Budgeting**: No budget creation, no alerts for overspending (V2 feature)
5. **Shared Accounts**: No multi-user households sharing a ledger (V2)
6. **Mobile App**: Web-only for MVP (React Native in V2)
7. **Cryptocurrency**: No crypto wallet tracking (future consideration)
8. **International Cards**: MVP focuses on US issuers; international support in V2

### Out of Scope (V2 / Future)
1. **Budget Creation & Alerts**: Set category budgets, get alerts when approaching limit
2. **Savings Goals**: Track progress toward financial goals (e.g., "Save $5k for vacation")
3. **Investment Tracking**: Link brokerage accounts, track portfolio
4. **Bill Predictions**: Predict upcoming bills based on historical data
5. **Multi-User Households**: Shared ledger for couples/families with permissions
6. **Tax Optimization**: Flag tax-deductible transactions, generate tax reports
7. **Receipt Image Capture**: OCR scan receipts for items purchased (itemized breakdown)
8. **Subscription Tracking**: Detect recurring subscriptions, flag unused ones

---

## User Stories (MVP)

### Epic 1: Email Ingestion
- **US-1.1**: As a user, I want to authorize Gmail access so the app can read my transaction emails
- **US-1.2**: As a user, I want the app to automatically sync new transactions daily so I don't have to manually check
- **US-1.3**: As a user, I want to see which emails were successfully parsed vs failed so I can manually add missing transactions
- **US-1.4**: As a user, I want duplicate transactions auto-detected so I don't see the same purchase twice

### Epic 2: Transaction Management
- **US-2.1**: As a user, I want to see all my transactions in one list (across all cards and P2P apps) so I have a unified view
- **US-2.2**: As a user, I want to filter transactions by date, card, category, and merchant so I can find specific purchases
- **US-2.3**: As a user, I want to edit transaction details (merchant name, category, notes) so the ledger is accurate
- **US-2.4**: As a user, I want to manually add transactions if email parsing failed so my ledger is complete

### Epic 3: Reimbursement Tracking
- **US-3.1**: As a user, I want to mark a transaction as reimbursed (full or partial) so I know my true out-of-pocket spending
- **US-3.2**: As a user, I want to see gross vs net spending per category so I understand reimbursement impact
- **US-3.3**: As a user, I want to see original purchase and reimbursement side-by-side so I can verify they match
- **US-3.4**: As a user, I want to track pending reimbursements so I know what I'm still owed

### Epic 4: Rewards Tracking
- **US-4.1**: As a user, I want to add my credit cards with reward structures so the app knows which card earns what
- **US-4.2**: As a user, I want to see rewards earned per transaction so I understand my points accumulation
- **US-4.3**: As a user, I want to see total rewards earned per card (monthly and all-time) so I can compare cards
- **US-4.4**: As a user, I want suggestions on which card to use for future purchases so I maximize rewards

### Epic 5: Insights & Dashboards
- **US-5.1**: As a user, I want to see a dashboard of this month's spending by category so I understand where my money goes
- **US-5.2**: As a user, I want to see my top merchants so I know who I spend the most with
- **US-5.3**: As a user, I want insights to link back to transactions so I can verify the data
- **US-5.4**: As a user, I want to export my transaction history to CSV so I can analyze it externally or share with an accountant

### Epic 6: Privacy & Security
- **US-6.1**: As a user, I want to see what permissions the app has and revoke Gmail access if needed so I control my data
- **US-6.2**: As a user, I want to delete my account and all data so I can leave the platform if desired
- **US-6.3**: As a user, I want assurance that my financial data is not sold or shared so I trust the app
- **US-6.4**: As a user, I want my OAuth tokens encrypted so my Gmail access is secure

---

## MVP vs V2 Feature Breakdown

### MVP Features (Launch in 3 Months)
- ✅ Gmail OAuth integration and email sync
- ✅ Transaction parsing for top 6 credit card issuers + Zelle/Venmo/Cash App
- ✅ Unified transaction ledger (list view, filtering, search)
- ✅ Manual transaction entry
- ✅ Merchant normalization (basic rules-based)
- ✅ Auto-categorization (rule-based + simple ML)
- ✅ Reimbursement tracking (mark as reimbursed, partial amounts)
- ✅ Credit card profile setup (name, last 4, reward rates)
- ✅ Rewards calculation per transaction and aggregated per card
- ✅ Basic rewards optimization suggestions
- ✅ Overview dashboard (spending by category, top merchants, recent transactions)
- ✅ Reimbursement dashboard (pending and completed)
- ✅ Rewards dashboard (per card, monthly total)
- ✅ Transaction export to CSV
- ✅ Account settings (manage payment methods, email sync preferences)
- ✅ Privacy controls (view/revoke OAuth, delete account)
- ✅ Mobile-responsive web app

### V2 Features (6-12 Months Post-Launch)
- 🔮 Automatic reimbursement matching (Zelle receipt → original purchase)
- 🔮 Bulk transaction operations (categorize, tag, export)
- 🔮 Custom categories and tags
- 🔮 Budget creation and alerts
- 🔮 Spending trends and anomaly detection
- 🔮 Points value tracking (redemption value in dollars)
- 🔮 Multi-currency support
- 🔮 Import historical transactions from CSV
- 🔮 Email/push notifications
- 🔮 Shared accounts (multi-user households)
- 🔮 Mobile app (React Native)
- 🔮 Subscription detection and tracking
- 🔮 Tax-deductible transaction flagging

---

## Privacy & Security Guarantees (Explicit)

### What We Collect
- **Email transaction data**: Merchant, amount, date, card last 4 (extracted from emails)
- **OAuth tokens**: Encrypted Gmail API refresh tokens
- **User profile**: Email address (from Google OAuth), timezone preference
- **User actions**: Audit logs of edits, deletions (for data integrity)

### What We DO NOT Collect
- ❌ Full email content (only extracted transaction fields)
- ❌ Bank account credentials or passwords
- ❌ Full credit card numbers (only last 4 digits)
- ❌ CVV, PIN, or security codes
- ❌ Social Security Number or tax IDs
- ❌ Biometric data
- ❌ Location data (unless explicitly provided in transaction)

### What We DO NOT Do With Your Data
- ❌ **Sell or share data** with third parties, affiliates, advertisers, or data brokers
- ❌ **Train ML models** on your data for other users' benefit (your data stays yours)
- ❌ **Use data for advertising** or targeted marketing
- ❌ **Share aggregated/anonymized data** (even anonymized, we don't share)
- ❌ **Retain data indefinitely** (audit logs purged after 90 days)

### What You Can Do
- ✅ **Export all data** in JSON or CSV format at any time
- ✅ **Delete account and all data** (irrecoverable after 30 days)
- ✅ **Revoke Gmail API access** without deleting account (pauses sync)
- ✅ **Review OAuth permissions** to see exactly what access the app has
- ✅ **Request data correction** if auto-parsed data is inaccurate

### Security Commitments
- 🔒 **Encrypted at rest**: OAuth tokens encrypted with AES-256, per-user keys in KMS
- 🔒 **Encrypted in transit**: TLS 1.3 for all API communication
- 🔒 **Access control**: Database-level checks ensure users only see their own data
- 🔒 **No plaintext secrets**: Credentials never logged or exposed in error messages
- 🔒 **Regular audits**: Quarterly security reviews and penetration testing (post-MVP)
- 🔒 **Incident response plan**: 24-hour notification if breach occurs

### Compliance
- **GDPR**: Right to access, right to delete, data portability, no automated profiling without consent
- **CCPA**: Do not sell user data (explicit policy), data export on request
- **OAuth 2.0 Best Practices**: Minimal scopes (readonly Gmail), refresh token rotation

---

## Open Questions & Decisions Needed

### Technical Decisions
1. **Background Job System**: Celery (production-grade, complex) vs APScheduler (simpler, good enough for MVP)?
   - **Recommendation**: APScheduler for MVP, migrate to Celery if job queue grows
2. **ML for Categorization**: Train custom model or use rule-based + off-the-shelf NLP?
   - **Recommendation**: Rule-based for MVP (faster, explainable), add ML in V2 if needed
3. **Email Parsing Library**: Custom regex vs existing parser (e.g., email-parser, mailgun)?
   - **Recommendation**: Custom regex for MVP (full control), evaluate libraries if maintenance burden grows

### Product Decisions
1. **Pricing Model**: Free tier + premium? Subscription only? One-time payment?
   - **Options**:
     - Free: 2 cards, 100 transactions/month
     - Premium ($5/mo): Unlimited cards, unlimited transactions, rewards optimization, export
   - **Decision**: Finalize pricing post-MVP based on user feedback
2. **Supported Email Providers**: Gmail only (MVP) or also Outlook, Yahoo?
   - **Recommendation**: Gmail only (80% of target users), add Outlook in V2
3. **Rewards Optimization Depth**: Basic suggestions (use Card X for dining) or advanced (consider annual fees, redemption value)?
   - **Recommendation**: Basic for MVP, advanced in V2

### Compliance Decisions
1. **GDPR Applicability**: Do we target EU users or US-only?
   - **Recommendation**: US-only for MVP (CCPA compliance), add GDPR compliance for EU expansion
2. **Data Residency**: Store data in US data centers only or support EU/Asia regions?
   - **Recommendation**: US-only for MVP, multi-region in V2

---

## Success Criteria (Launch Readiness)

### Must-Have (Blockers to Launch)
- ✅ OAuth 2.0 authentication works (Google sign-in)
- ✅ Gmail API integration syncs emails and parses 5+ credit card issuers correctly
- ✅ Transactions display in unified ledger (list view, filtering works)
- ✅ Reimbursement tracking functional (mark as reimbursed, see net spending)
- ✅ Rewards calculation accurate (per transaction and aggregated)
- ✅ Export to CSV works
- ✅ Privacy policy published (plain English, no data sales clause)
- ✅ Data deletion works (user can delete account and verify data removed)
- ✅ Security: OAuth tokens encrypted, HTTPS everywhere
- ✅ Performance: Page load < 2s, transaction list < 500ms

### Nice-to-Have (Can defer post-launch)
- 🟡 Automatic merchant normalization (can improve post-launch)
- 🟡 Advanced rewards optimization (basic suggestions sufficient for MVP)
- 🟡 Mobile app polish (web responsiveness sufficient for MVP)
- 🟡 Multi-currency support (US-only for MVP)

### Launch Blockers (Red Flags)
- 🚨 Gmail API quota exceeded (can't sync for all users)
- 🚨 OAuth refresh token encryption broken (security vulnerability)
- 🚨 Transaction parsing accuracy < 70% (too much manual entry)
- 🚨 Data leakage (user can see another user's transactions)
- 🚨 Privacy policy missing or ambiguous

---

## Risks & Mitigations

### Risk 1: Gmail API Quota Limits
- **Impact**: Can't sync emails for all users, app becomes unusable
- **Probability**: Medium (Gmail API has generous free tier, but scaling may hit limits)
- **Mitigation**:
  - Monitor API usage closely
  - Request quota increase from Google preemptively
  - Implement intelligent polling (only check for new emails, not full inbox scan)

### Risk 2: Email Parsing Accuracy
- **Impact**: Users frustrated by manual corrections, abandon app
- **Probability**: Medium-High (email formats vary widely)
- **Mitigation**:
  - Start with top 6 issuers (cover 80% of users)
  - Crowdsource parsing rules (users submit failed emails for debugging)
  - Provide easy manual entry fallback

### Risk 3: User Trust / Privacy Concerns
- **Impact**: Users hesitant to grant Gmail access, low adoption
- **Probability**: Medium (fintech privacy concerns are real)
- **Mitigation**:
  - Transparent privacy policy (plain English, no data sales)
  - Educational content: "We only read transaction emails, not personal emails"
  - OAuth scopes: Request minimal permissions (readonly Gmail, not full inbox access)
  - Testimonials from beta users

### Risk 4: Competitive Pressure
- **Impact**: Mint, YNAB, or new entrant copies our approach
- **Probability**: Low-Medium (email-first approach is novel)
- **Mitigation**:
  - Move fast (launch MVP in 3 months)
  - Build moat: Superior reimbursement tracking and rewards optimization
  - Community engagement: Build loyal user base

### Risk 5: Regulatory Changes
- **Impact**: New fintech regulations require bank-grade compliance (costly)
- **Probability**: Low (read-only email parsing less regulated than payment processing)
- **Mitigation**:
  - Stay informed on CFPB, GDPR updates
  - Legal review before launch
  - Flexible architecture to add compliance features if needed

---

## Timeline & Milestones

### Milestone 1: Backend Core (4 weeks)
- FastAPI setup with PostgreSQL
- User authentication (OAuth 2.0)
- Gmail API integration (read emails)
- Transaction parsing logic (top 3 issuers: Amex, Chase, Citi)
- Database models (users, transactions, payment_methods)
- API endpoints (CRUD transactions)

### Milestone 2: Frontend Core (4 weeks, parallel with M1)
- Next.js setup with Tailwind + shadcn/ui
- OAuth login flow
- Transaction list view (table with filtering)
- Transaction detail view (edit, delete)
- Manual transaction entry form
- Dashboard (basic spending by category)

### Milestone 3: Feature Completeness (4 weeks)
- Email parsing for all MVP issuers (6 cards + 3 P2P apps)
- Merchant normalization logic
- Auto-categorization (rule-based)
- Reimbursement tracking (mark as reimbursed, net spending)
- Credit card profile setup
- Rewards calculation and dashboard
- Export to CSV

### Milestone 4: Polish & Beta (2 weeks)
- Mobile responsiveness
- Error handling and user messaging
- Onboarding flow (OAuth → sync → tour)
- Privacy policy page
- Help/FAQ page
- Beta testing with 10 users, gather feedback

### Milestone 5: Launch (1 week)
- Bug fixes from beta
- Performance optimization (page load, email sync)
- Launch checklist (security review, backup tested, monitoring setup)
- Public launch (Product Hunt, social media, invite-only beta expansion)

**Total MVP Timeline: 15 weeks (3.5 months)**

---

## Appendix

### A. Example Email Parsing Rules
**Amex:**
- Pattern: "You used your Card ending in XXXX for $Y.YY at MERCHANT on MM/DD/YYYY"
- Extract: amount=$Y.YY, merchant=MERCHANT, date=MM/DD/YYYY, last4=XXXX

**Chase:**
- Pattern: "Your Chase card ending in XXXX was used for a $Y.YY transaction at MERCHANT"
- Extract: amount=$Y.YY, merchant=MERCHANT, last4=XXXX

**Zelle:**
- Pattern: "You sent $Y.YY to NAME with Zelle on MM/DD/YYYY"
- Extract: amount=$Y.YY, merchant=Zelle (to NAME), date=MM/DD/YYYY

### B. Merchant Normalization Examples
- "AMZN*MARKETPLACE" → "Amazon"
- "SQ *COFFEE SHOP NYC" → "Square - Coffee Shop"
- "TST* RESTAURANT NAME" → "Toast - Restaurant Name"
- "PAYPAL *EBAY" → "PayPal (eBay)"

### C. Reward Structure Examples
**Chase Sapphire Reserve:**
- 3% on travel and dining
- 1% on everything else
- Annual fee: $550
- Signup bonus: 60,000 points

**Amex Blue Cash Preferred:**
- 6% on groceries (up to $6k/year)
- 3% on gas and transit
- 1% on everything else
- Annual fee: $95

### D. Privacy Policy Key Points (Summary)
- We only access emails containing financial transaction notifications
- We do not sell, share, or monetize your data
- OAuth tokens are encrypted at rest (AES-256)
- You can delete your account and all data at any time
- We comply with GDPR (right to access, right to delete, data portability)
- We do not use your data to train ML models for other users

---

## Document History

| Version | Date       | Author           | Changes                          |
|---------|------------|------------------|----------------------------------|
| 1.0     | 2026-02-11 | Product & Eng    | Initial draft (MVP requirements) |

---

**Next Steps:**
1. Review and approve PRD with stakeholders
2. Refine technical architecture (see [claude.md](../claude.md))
3. Define database schema (core domain model)
4. Design API contracts (OpenAPI spec)
5. Begin Milestone 1 (Backend Core)

**Questions? Contact**: product@spendi.app