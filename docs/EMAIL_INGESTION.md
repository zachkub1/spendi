# Email Ingestion System: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Engineering

---

## Overview

The email ingestion system automatically extracts financial transaction data from Gmail using the Gmail API. The system is designed to be:

1. **Idempotent**: Processing the same email multiple times produces the same result
2. **Privacy-First**: Email content never stored long-term (only extracted fields)
3. **Resilient**: Failed parsing retried with exponential backoff
4. **Extensible**: Easy to add new email formats and providers

---

## Table of Contents

1. [Ingestion Pipeline Architecture](#ingestion-pipeline-architecture)
2. [Pipeline Stages](#pipeline-stages)
3. [Gmail API Integration](#gmail-api-integration)
4. [Parsing Strategy](#parsing-strategy)
5. [Email Format Parsers](#email-format-parsers)
6. [Duplicate Detection](#duplicate-detection)
7. [Error Handling & Retry Logic](#error-handling--retry-logic)
8. [Implementation Guide](#implementation-guide)
9. [Testing Strategy](#testing-strategy)

---

## Ingestion Pipeline Architecture

### High-Level Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│ Ingestion Pipeline (Daily Scheduled Job)                             │
└──────────────────────────────────────────────────────────────────────┘

Stage 1: DISCOVERY
├─ Query Gmail API for new financial emails (since last sync)
├─ Filter by sender allowlist (chase.com, venmo.com, etc.)
├─ Fetch message metadata (ID, subject, date, sender)
└─ Create RawEmail records (status: pending)

Stage 2: FETCHING
├─ For each RawEmail with status=pending:
├─ Fetch full email body (text + HTML)
├─ Extract relevant fields (subject, sender, body)
└─ Update RawEmail (status: fetched)

Stage 3: PARSING
├─ For each RawEmail with status=fetched:
├─ Detect email format (Chase, Amex, Venmo, etc.)
├─ Apply format-specific parser (regex + rules)
├─ Extract transaction data (merchant, amount, date, card last 4)
├─ Create ParsedTransaction record
└─ Update RawEmail (status: success or failed)

Stage 4: NORMALIZATION
├─ For each ParsedTransaction not yet normalized:
├─ Match payment instrument (by last 4 digits or account identifier)
├─ Normalize merchant name (clean up raw strings)
├─ Auto-categorize (rule-based + ML)
├─ Create NormalizedTransaction record
└─ Update ParsedTransaction (normalized: true)

Stage 5: CLEANUP
├─ Delete email content from RawEmail records (keep metadata only)
├─ Archive old RawEmail records (>90 days)
└─ Log sync completion to audit trail
```

---

## Pipeline Stages

### Stage 1: Discovery (Gmail API Query)

**Purpose**: Find new financial emails since last sync

**Process**:
1. Retrieve last sync timestamp from `EmailAccount.last_sync_at`
2. Query Gmail API with sender allowlist and date filter
3. Fetch message IDs and metadata (subject, sender, date)
4. Create `RawEmail` records with `parsing_status = 'pending'`
5. **Idempotency**: Skip emails with existing `RawEmail.message_id` (duplicate detection)

**Gmail API Call**:
```python
query = f"from:({' OR '.join(ALLOWED_SENDERS)}) after:{last_sync_date}"
response = gmail_service.users().messages().list(
    userId='me',
    q=query,
    maxResults=500
).execute()
```

**Output**: List of `RawEmail` IDs to process

---

### Stage 2: Fetching (Get Email Bodies)

**Purpose**: Fetch full email content for parsing

**Process**:
1. For each `RawEmail` with `parsing_status = 'pending'`:
2. Fetch full message using Gmail API (`messages.get`)
3. Extract plaintext and HTML bodies
4. Store temporarily in memory (not persisted)
5. Update `RawEmail.parsing_status = 'fetched'`

**Gmail API Call**:
```python
message = gmail_service.users().messages().get(
    userId='me',
    id=message_id,
    format='full'
).execute()

# Extract body
payload = message['payload']
body_text = extract_body_text(payload)  # Helper function
body_html = extract_body_html(payload)
```

**Output**: Email bodies ready for parsing (in memory)

---

### Stage 3: Parsing (Extract Transaction Data)

**Purpose**: Extract structured transaction data from unstructured email

**Process**:
1. Detect email format (Chase, Amex, Venmo, etc.)
2. Apply format-specific parser:
   - **Rule-based**: Regex patterns for known formats
   - **NLP fallback**: Use spaCy/LLM for unknown formats
3. Extract fields: merchant, amount, date, card last 4, transaction type
4. Assign confidence score (0-100)
5. Create `ParsedTransaction` record
6. Update `RawEmail.parsing_status`:
   - `'success'` if parsed
   - `'failed'` if parsing failed (retry later)

**Parser Selection Logic**:
```python
def select_parser(sender: str, subject: str) -> Parser:
    if "chase.com" in sender:
        return ChaseParser()
    elif "americanexpress.com" in sender:
        return AmexParser()
    elif "venmo.com" in sender:
        return VenmoParser()
    elif "zelle.com" in sender:
        return ZelleParser()
    else:
        return GenericNLPParser()  # Fallback
```

**Output**: `ParsedTransaction` records with extracted data

---

### Stage 4: Normalization (Clean & Enrich)

**Purpose**: Convert parsed data into finalized ledger entries

**Process**:
1. **Match Payment Instrument**:
   - Credit/Debit Cards: Match by `last_four_digits`
   - P2P Accounts: Match by `account_identifier` (e.g., Venmo username)
   - If no match: Flag for user to add payment method
2. **Normalize Merchant**:
   - Clean raw merchant string: `"SQ *BLUE BOTTLE"` → `"Blue Bottle Coffee"`
   - Use merchant normalization rules (see below)
3. **Auto-Categorize**:
   - Apply rule-based categorization (e.g., Starbucks → Dining)
   - Fallback to ML model if no rule matches
   - Assign confidence score
4. Create `NormalizedTransaction` record
5. Update `ParsedTransaction.normalized = true`

**Output**: `NormalizedTransaction` ready for user viewing

---

### Stage 5: Cleanup (Privacy Compliance)

**Purpose**: Delete email content to minimize data retention

**Process**:
1. For all `RawEmail` records with `parsing_status = 'success'`:
   - Delete email content (subject and body fields)
   - Keep only metadata (message_id, sender, date, parsing status)
2. Archive old `RawEmail` records (>90 days) to cold storage
3. Log sync completion to audit trail

**Data Retention**:
- **Kept**: `message_id`, `sender_email`, `received_at`, `parsing_status`
- **Deleted**: `subject`, `body_text`, `body_html`

---

## Gmail API Integration

### Authentication

**OAuth Scope**: `https://www.googleapis.com/auth/gmail.readonly`

**Token Refresh** (before each sync):
```python
from googleapiclient.discovery import build
from app.auth.encryption import decrypt_token

def get_gmail_service(email_account: EmailAccount):
    """Get authenticated Gmail API service."""
    # Decrypt refresh token
    refresh_token = decrypt_token(
        email_account.oauth_refresh_token,
        email_account.encryption_key,
        email_account.encryption_iv,
        email_account.user_id
    )

    # Refresh access token if expired
    if email_account.oauth_token_expires_at < datetime.utcnow():
        credentials = refresh_oauth_token(refresh_token)
        # Update access token in DB (encrypted)
        update_access_token(email_account, credentials.token)
    else:
        credentials = build_credentials(email_account.oauth_access_token)

    # Build Gmail API client
    service = build('gmail', 'v1', credentials=credentials)
    return service
```

---

### Gmail Query Filters (Per Provider)

**Goal**: Only fetch transaction-related emails (not personal emails)

#### Credit Card Issuers

**Chase:**
```python
query = 'from:(chase.com) subject:("card" OR "transaction" OR "purchase")'
```
- Matches: `no-reply@chase.com`, `alerts@chase.com`
- Excludes: Marketing emails, account statements

**American Express:**
```python
query = 'from:(americanexpress.com) subject:("charge" OR "transaction" OR "approved")'
```

**Citi:**
```python
query = 'from:(citi.com) subject:("transaction" OR "purchase")'
```

**Discover:**
```python
query = 'from:(discover.com) subject:("transaction" OR "purchase")'
```

**Capital One:**
```python
query = 'from:(capitalone.com) subject:("transaction" OR "purchase")'
```

**Bank of America:**
```python
query = 'from:(bankofamerica.com) subject:("transaction" OR "purchase")'
```

#### P2P Payment Apps

**Venmo:**
```python
query = 'from:(venmo.com) subject:("You paid" OR "You received")'
```

**Zelle:**
```python
query = 'from:(zelle.com) subject:("sent you" OR "You sent")'
```

**Cash App:**
```python
query = 'from:(cash.app) subject:("sent" OR "received")'
```

**PayPal:**
```python
query = 'from:(paypal.com) subject:("You sent" OR "You received")'
```

---

### Combined Query (All Providers)

```python
ALLOWED_SENDERS = {
    'chase.com': 'subject:("card" OR "transaction")',
    'americanexpress.com': 'subject:("charge" OR "transaction")',
    'citi.com': 'subject:("transaction" OR "purchase")',
    'discover.com': 'subject:("transaction" OR "purchase")',
    'capitalone.com': 'subject:("transaction" OR "purchase")',
    'venmo.com': 'subject:("You paid" OR "You received")',
    'zelle.com': 'subject:("sent you" OR "You sent")',
    'cash.app': 'subject:("sent" OR "received")'
}

# Build query
queries = [f"from:{sender} {filters}" for sender, filters in ALLOWED_SENDERS.items()]
full_query = f"({' OR '.join(queries)}) after:{last_sync_date}"
```

**Example Full Query**:
```
(from:chase.com subject:("card" OR "transaction") OR from:venmo.com subject:("You paid" OR "You received")) after:2026/02/10
```

---

### Rate Limiting & Pagination

**Gmail API Quotas** (as of 2026):
- **Daily quota**: 1 billion requests/day (per project)
- **Per-user quota**: 250 requests/second

**Pagination**:
```python
def fetch_all_messages(service, query, max_results=500):
    """Fetch all messages matching query (with pagination)."""
    all_messages = []
    page_token = None

    while True:
        response = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results,
            pageToken=page_token
        ).execute()

        messages = response.get('messages', [])
        all_messages.extend(messages)

        page_token = response.get('nextPageToken')
        if not page_token:
            break

    return all_messages
```

**Rate Limit Handling**:
```python
import time
from googleapiclient.errors import HttpError

def fetch_with_retry(service, message_id, max_retries=3):
    """Fetch message with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
        except HttpError as e:
            if e.resp.status == 429:  # Rate limit exceeded
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
    raise Exception(f"Failed to fetch message after {max_retries} retries")
```

---

## Parsing Strategy

### Two-Tier Approach: Rules + NLP Fallback

**Tier 1: Rule-Based Parsers (High Confidence)**
- Hand-crafted regex patterns for known email formats
- Fast, deterministic, explainable
- Covers 80-90% of emails (from major issuers)

**Tier 2: NLP Fallback (Medium Confidence)**
- Named Entity Recognition (NER) using spaCy or LLM
- Extracts merchant, amount, date from unstructured text
- Covers edge cases, new formats, regional banks

---

### Rule-Based Parsing (Regex)

**Advantages**:
- ✅ Fast (no API calls or ML inference)
- ✅ Deterministic (same input → same output)
- ✅ Explainable (show regex pattern to user)
- ✅ High confidence (99%+ accuracy for known formats)

**Disadvantages**:
- ❌ Brittle (breaks if email format changes)
- ❌ Maintenance overhead (update regex when issuers change templates)
- ❌ Doesn't generalize (new issuer = new parser)

**Example: Chase Transaction Email**

**Email Sample**:
```
Subject: Your Chase card was used

Your Chase Sapphire Reserve card ending in 5678 was used for a
$12.50 transaction at SQ *BLUE BOTTLE COFFEE on 02/10/2026 at 2:15 PM.

If this wasn't you, let us know immediately.
```

**Regex Parser**:
```python
import re
from datetime import datetime
from decimal import Decimal

class ChaseParser:
    PATTERN = re.compile(
        r"Your Chase (?P<card_name>[\w\s]+) card ending in (?P<last_four>\d{4}) "
        r"was used for a \$(?P<amount>[\d,]+\.\d{2}) transaction at "
        r"(?P<merchant>.+?) on (?P<date>\d{2}/\d{2}/\d{4})",
        re.IGNORECASE
    )

    def parse(self, email_body: str) -> dict:
        match = self.PATTERN.search(email_body)
        if not match:
            raise ParsingError("No match found")

        return {
            'merchant_raw': match.group('merchant'),
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.strptime(match.group('date'), '%m/%d/%Y').date(),
            'payment_instrument_hint': match.group('last_four'),
            'transaction_type': 'purchase',
            'confidence_score': 95
        }
```

**Test Cases**:
```python
def test_chase_parser():
    parser = ChaseParser()

    # Test case 1: Standard purchase
    email = "Your Chase Sapphire Reserve card ending in 5678 was used for a $12.50 transaction at SQ *BLUE BOTTLE COFFEE on 02/10/2026 at 2:15 PM."
    result = parser.parse(email)
    assert result['amount'] == Decimal('12.50')
    assert result['merchant_raw'] == 'SQ *BLUE BOTTLE COFFEE'
    assert result['payment_instrument_hint'] == '5678'

    # Test case 2: Large amount with comma
    email = "Your Chase Freedom card ending in 1234 was used for a $1,234.56 transaction at AMAZON.COM on 02/09/2026."
    result = parser.parse(email)
    assert result['amount'] == Decimal('1234.56')
```

---

### NLP Fallback (Named Entity Recognition)

**When to Use**:
- Unknown email format (not in parser registry)
- Parsing confidence < 70%
- Regional banks or new issuers

**Approach 1: spaCy NER** (Fast, Offline)

```python
import spacy
from decimal import Decimal

nlp = spacy.load("en_core_web_sm")

class GenericNLPParser:
    def parse(self, email_body: str) -> dict:
        doc = nlp(email_body)

        # Extract entities
        merchant = self._extract_merchant(doc)
        amount = self._extract_amount(email_body)
        date = self._extract_date(doc)

        return {
            'merchant_raw': merchant,
            'amount': amount,
            'transaction_date': date,
            'payment_instrument_hint': None,  # Unknown
            'transaction_type': 'purchase',
            'confidence_score': 60  # Lower confidence
        }

    def _extract_amount(self, text: str) -> Decimal:
        """Extract dollar amounts using regex."""
        pattern = r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(pattern, text)
        if matches:
            return Decimal(matches[0].replace(',', ''))
        return None

    def _extract_date(self, doc):
        """Extract dates using spaCy NER."""
        for ent in doc.ents:
            if ent.label_ == 'DATE':
                # Parse date (handle various formats)
                return parse_date(ent.text)
        return None

    def _extract_merchant(self, doc):
        """Extract merchant name (ORG entities)."""
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                return ent.text
        return "Unknown Merchant"
```

**Approach 2: LLM-based Parsing** (High Accuracy, Expensive)

```python
import openai

class LLMParser:
    def parse(self, email_body: str) -> dict:
        """Use OpenAI GPT to extract transaction data."""
        prompt = f"""
        Extract transaction information from this email:

        {email_body}

        Return JSON with these fields:
        - merchant: The merchant/store name
        - amount: Dollar amount (number only)
        - date: Transaction date (YYYY-MM-DD format)
        - card_last_4: Last 4 digits of card (if mentioned)
        - transaction_type: "purchase", "refund", "payment", or "transfer"
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a transaction data extractor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )

        result = json.loads(response.choices[0].message.content)
        return {
            'merchant_raw': result['merchant'],
            'amount': Decimal(result['amount']),
            'transaction_date': datetime.strptime(result['date'], '%Y-%m-%d').date(),
            'payment_instrument_hint': result.get('card_last_4'),
            'transaction_type': result['transaction_type'],
            'confidence_score': 75  # Medium confidence (LLM may hallucinate)
        }
```

**Trade-offs**:
| Approach | Speed | Cost | Accuracy | Offline |
|----------|-------|------|----------|---------|
| Regex | Fast | Free | 95%+ (known formats) | ✅ |
| spaCy NER | Fast | Free | 60-70% (generic) | ✅ |
| LLM (GPT-4) | Slow | $0.01/email | 80-90% (generic) | ❌ |

**Recommendation**: Use regex for known formats, spaCy for fallback, LLM for high-value users (premium tier)

---

## Email Format Parsers

### Chase

**Email Patterns**:
1. **Purchase Confirmation**:
   ```
   Subject: Your Chase card was used
   Body: Your Chase [Card Name] card ending in [XXXX] was used for a $[amount] transaction at [Merchant] on [date].
   ```

2. **Refund Notification**:
   ```
   Subject: A refund was processed
   Body: A refund of $[amount] was processed to your Chase [Card Name] card ending in [XXXX] from [Merchant].
   ```

**Parser**:
```python
class ChaseParser:
    PURCHASE_PATTERN = re.compile(
        r"Your Chase (?P<card_name>[\w\s]+) card ending in (?P<last_four>\d{4}) "
        r"was used for a \$(?P<amount>[\d,]+\.\d{2}) transaction at "
        r"(?P<merchant>.+?) on (?P<date>\d{2}/\d{2}/\d{4})",
        re.IGNORECASE | re.DOTALL
    )

    REFUND_PATTERN = re.compile(
        r"A refund of \$(?P<amount>[\d,]+\.\d{2}) was processed to your "
        r"Chase (?P<card_name>[\w\s]+) card ending in (?P<last_four>\d{4}) "
        r"from (?P<merchant>.+?)\.",
        re.IGNORECASE
    )

    def parse(self, email_body: str, subject: str) -> dict:
        # Try refund pattern first
        if 'refund' in subject.lower():
            match = self.REFUND_PATTERN.search(email_body)
            if match:
                return self._extract_refund(match)

        # Try purchase pattern
        match = self.PURCHASE_PATTERN.search(email_body)
        if match:
            return self._extract_purchase(match)

        raise ParsingError("No known Chase pattern matched")

    def _extract_purchase(self, match) -> dict:
        return {
            'merchant_raw': match.group('merchant').strip(),
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.strptime(match.group('date'), '%m/%d/%Y').date(),
            'payment_instrument_hint': match.group('last_four'),
            'transaction_type': 'purchase',
            'confidence_score': 95
        }

    def _extract_refund(self, match) -> dict:
        return {
            'merchant_raw': match.group('merchant').strip(),
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.utcnow().date(),  # Assume today
            'payment_instrument_hint': match.group('last_four'),
            'transaction_type': 'refund',
            'confidence_score': 90
        }
```

---

### American Express

**Email Pattern**:
```
Subject: Charge on your Amex account

Hello [Name],

A charge of $[amount] at [Merchant] was approved on your Card
ending in [XXXX] on [date].
```

**Parser**:
```python
class AmexParser:
    PATTERN = re.compile(
        r"A charge of \$(?P<amount>[\d,]+\.\d{2}) at (?P<merchant>.+?) "
        r"was approved on your Card ending in (?P<last_four>\d{4}) "
        r"on (?P<date>\w+ \d{1,2}, \d{4})",
        re.IGNORECASE
    )

    def parse(self, email_body: str) -> dict:
        match = self.PATTERN.search(email_body)
        if not match:
            raise ParsingError("No Amex pattern matched")

        return {
            'merchant_raw': match.group('merchant').strip(),
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.strptime(match.group('date'), '%B %d, %Y').date(),
            'payment_instrument_hint': match.group('last_four'),
            'transaction_type': 'purchase',
            'confidence_score': 95
        }
```

---

### Venmo

**Email Pattern**:
```
Subject: You paid [Name] $[amount]

You paid [Name] $[amount].

[Date]
```

**Parser**:
```python
class VenmoParser:
    SENT_PATTERN = re.compile(
        r"You paid (?P<recipient>.+?) \$(?P<amount>[\d,]+\.\d{2})",
        re.IGNORECASE
    )

    RECEIVED_PATTERN = re.compile(
        r"(?P<sender>.+?) paid you \$(?P<amount>[\d,]+\.\d{2})",
        re.IGNORECASE
    )

    def parse(self, email_body: str, subject: str) -> dict:
        # Determine transaction direction
        if 'You paid' in subject:
            match = self.SENT_PATTERN.search(email_body)
            if match:
                return {
                    'merchant_raw': f"Venmo - {match.group('recipient')}",
                    'amount': Decimal(match.group('amount').replace(',', '')),
                    'transaction_date': datetime.utcnow().date(),  # Use today
                    'payment_instrument_hint': None,
                    'transaction_type': 'transfer',
                    'confidence_score': 90
                }
        elif 'paid you' in subject:
            match = self.RECEIVED_PATTERN.search(email_body)
            if match:
                return {
                    'merchant_raw': f"Venmo from {match.group('sender')}",
                    'amount': Decimal(match.group('amount').replace(',', '')),
                    'transaction_date': datetime.utcnow().date(),
                    'transaction_type': 'transfer',
                    'confidence_score': 90
                }

        raise ParsingError("No Venmo pattern matched")
```

---

### Zelle

**Email Pattern**:
```
Subject: [Name] sent you $[amount] with Zelle

[Name] sent you $[amount] with Zelle on [date].
```

**Parser**:
```python
class ZelleParser:
    SENT_PATTERN = re.compile(
        r"You sent \$(?P<amount>[\d,]+\.\d{2}) to (?P<recipient>.+?) with Zelle",
        re.IGNORECASE
    )

    RECEIVED_PATTERN = re.compile(
        r"(?P<sender>.+?) sent you \$(?P<amount>[\d,]+\.\d{2}) with Zelle",
        re.IGNORECASE
    )

    def parse(self, email_body: str, subject: str) -> dict:
        if 'You sent' in subject:
            match = self.SENT_PATTERN.search(email_body)
            merchant = f"Zelle to {match.group('recipient')}"
        else:
            match = self.RECEIVED_PATTERN.search(email_body)
            merchant = f"Zelle from {match.group('sender')}"

        if not match:
            raise ParsingError("No Zelle pattern matched")

        return {
            'merchant_raw': merchant,
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.utcnow().date(),
            'payment_instrument_hint': None,
            'transaction_type': 'transfer',
            'confidence_score': 90
        }
```

---

### Cash App

**Email Pattern**:
```
Subject: You sent $[amount]

You sent $[amount] to [Name] on [date].
```

**Parser**:
```python
class CashAppParser:
    PATTERN = re.compile(
        r"You (?P<action>sent|received) \$(?P<amount>[\d,]+\.\d{2}) "
        r"(?:to|from) (?P<contact>.+?) on",
        re.IGNORECASE
    )

    def parse(self, email_body: str) -> dict:
        match = self.PATTERN.search(email_body)
        if not match:
            raise ParsingError("No Cash App pattern matched")

        action = match.group('action').lower()
        contact = match.group('contact')

        return {
            'merchant_raw': f"Cash App {'to' if action == 'sent' else 'from'} {contact}",
            'amount': Decimal(match.group('amount').replace(',', '')),
            'transaction_date': datetime.utcnow().date(),
            'payment_instrument_hint': None,
            'transaction_type': 'transfer',
            'confidence_score': 90
        }
```

---

## Duplicate Detection

### Problem Statement

**Scenario**: Credit card transaction notifications often come in multiple emails:
1. **Authorization email**: "Your card was used for $X at Merchant" (when swiped)
2. **Settlement email**: "Transaction settled for $X at Merchant" (1-3 days later)

**Goal**: Detect duplicates and only create one `NormalizedTransaction`

---

### Detection Strategy

**Three-Level Deduplication**:

#### Level 1: Gmail Message ID (Prevents Re-Processing)

**Check**: Before creating `RawEmail`, check if `message_id` already exists

```python
def is_duplicate_email(message_id: str, db) -> bool:
    """Check if email already processed."""
    existing = db.query(RawEmail).filter(
        RawEmail.message_id == message_id
    ).first()
    return existing is not None
```

**Idempotency**: Running sync job multiple times won't create duplicate `RawEmail` records

---

#### Level 2: External Transaction ID (Issuer-Provided)

**Check**: Some emails include transaction IDs (e.g., Chase `Ref: 123456789`)

```python
class ChaseParser:
    TRANSACTION_ID_PATTERN = re.compile(r"Ref:\s*(?P<txn_id>\d+)")

    def parse(self, email_body: str) -> dict:
        # ... existing parsing logic ...

        # Extract transaction ID
        txn_id_match = self.TRANSACTION_ID_PATTERN.search(email_body)
        external_txn_id = txn_id_match.group('txn_id') if txn_id_match else None

        return {
            # ... other fields ...
            'transaction_id_external': external_txn_id
        }
```

**Deduplication Query**:
```python
def is_duplicate_transaction(parsed_txn: ParsedTransaction, db) -> bool:
    """Check if transaction already exists (by external ID)."""
    if not parsed_txn.transaction_id_external:
        return False  # No external ID, can't deduplicate

    existing = db.query(ParsedTransaction).filter(
        ParsedTransaction.transaction_id_external == parsed_txn.transaction_id_external,
        ParsedTransaction.user_id == parsed_txn.user_id
    ).first()

    return existing is not None
```

---

#### Level 3: Fuzzy Match (Amount + Date + Merchant + Card)

**Check**: For transactions without external IDs, use fuzzy matching

```python
from datetime import timedelta

def find_similar_transaction(
    parsed_txn: ParsedTransaction,
    db,
    date_window_days: int = 3
) -> Optional[ParsedTransaction]:
    """Find similar transaction within date window."""
    date_min = parsed_txn.transaction_date - timedelta(days=date_window_days)
    date_max = parsed_txn.transaction_date + timedelta(days=date_window_days)

    candidates = db.query(ParsedTransaction).filter(
        ParsedTransaction.user_id == parsed_txn.user_id,
        ParsedTransaction.amount == parsed_txn.amount,  # Exact match
        ParsedTransaction.transaction_date.between(date_min, date_max),
        ParsedTransaction.payment_instrument_hint == parsed_txn.payment_instrument_hint
    ).all()

    for candidate in candidates:
        # Fuzzy match merchant name
        similarity = merchant_similarity(
            parsed_txn.merchant_raw,
            candidate.merchant_raw
        )
        if similarity > 0.8:  # 80% similar
            return candidate

    return None


def merchant_similarity(merchant1: str, merchant2: str) -> float:
    """Calculate similarity between merchant names (0-1)."""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, merchant1.lower(), merchant2.lower()).ratio()
```

**Example**:
- Email 1: `"SQ *BLUE BOTTLE COFFEE"`, date: `2026-02-10`, amount: `$12.50`, card: `5678`
- Email 2: `"BLUE BOTTLE COFFEE #123"`, date: `2026-02-11`, amount: `$12.50`, card: `5678`
- Similarity: 85% → Mark as duplicate

---

### Handling Duplicates

**Strategy**: Keep first parsed transaction, discard duplicates

```python
def process_parsed_transaction(parsed_txn: ParsedTransaction, db):
    """Normalize transaction if not duplicate."""
    # Level 2: Check external transaction ID
    if is_duplicate_transaction(parsed_txn, db):
        logger.info(f"Duplicate transaction detected (external ID): {parsed_txn.id}")
        return

    # Level 3: Check fuzzy match
    similar_txn = find_similar_transaction(parsed_txn, db)
    if similar_txn:
        logger.info(f"Duplicate transaction detected (fuzzy match): {parsed_txn.id}")
        # Link to original
        parsed_txn.duplicate_of_id = similar_txn.id
        db.commit()
        return

    # Not duplicate, proceed to normalization
    normalize_transaction(parsed_txn, db)
```

---

## Error Handling & Retry Logic

### Failure Modes

1. **Gmail API Failure** (429 rate limit, 500 server error)
2. **Parsing Failure** (unknown email format, malformed data)
3. **Normalization Failure** (no payment instrument match)

---

### Retry Strategy

**Exponential Backoff with Max Retries**:

```python
from celery import Task

class EmailSyncTask(Task):
    autoretry_for = (HttpError,)  # Retry on Gmail API errors
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes
    retry_jitter = True  # Add randomness to avoid thundering herd

@app.task(base=EmailSyncTask)
def sync_email_account(email_account_id: str):
    """Sync emails for an account (with retry)."""
    try:
        email_account = get_email_account(email_account_id)
        gmail_service = get_gmail_service(email_account)

        # Stage 1: Discovery
        messages = discover_new_messages(gmail_service, email_account)

        # Stage 2-4: Fetch, Parse, Normalize
        for message in messages:
            process_message(message, gmail_service, email_account)

        # Stage 5: Cleanup
        cleanup_email_content(email_account)

        # Update last sync timestamp
        email_account.last_sync_at = datetime.utcnow()
        email_account.last_sync_status = 'success'
        db.commit()

    except Exception as e:
        logger.error(f"Email sync failed for {email_account_id}: {str(e)}")
        email_account.last_sync_status = 'failed'
        db.commit()
        raise  # Re-raise for Celery retry
```

**Retry Schedule**:
- Attempt 1: Immediate
- Attempt 2: 2 minutes later
- Attempt 3: 4 minutes later
- Attempt 4: 8 minutes later (max retries reached, mark as failed)

---

### Partial Failure Handling

**Scenario**: 100 new emails, 95 parsed successfully, 5 failed

**Strategy**: Process successfully parsed emails, flag failures for manual review

```python
def process_message(message_id: str, gmail_service, email_account):
    """Process a single email (catch exceptions)."""
    try:
        # Fetch email
        email = fetch_email(gmail_service, message_id)

        # Parse
        parsed_txn = parse_email(email, email_account)

        # Normalize
        normalized_txn = normalize_transaction(parsed_txn)

        logger.info(f"Successfully processed message {message_id}")

    except ParsingError as e:
        # Parsing failed, mark for manual review
        logger.warning(f"Parsing failed for {message_id}: {str(e)}")
        create_failed_parse_record(message_id, email_account, error=str(e))

    except Exception as e:
        # Unexpected error, log and continue
        logger.error(f"Unexpected error processing {message_id}: {str(e)}")
        # Don't raise (continue processing other messages)
```

---

## Implementation Guide

### Celery Background Job

**File: `backend/app/jobs/email_sync.py`**

```python
from celery import Celery
from app.db.session import get_db
from app.db.models import EmailAccount
from datetime import datetime

app = Celery('spendi', broker='redis://localhost:6379/0')

@app.task
def sync_all_email_accounts():
    """Scheduled job: Sync all active email accounts."""
    db = next(get_db())

    # Get all email accounts with sync enabled
    email_accounts = db.query(EmailAccount).filter(
        EmailAccount.sync_enabled == True
    ).all()

    for email_account in email_accounts:
        # Trigger sync for each account (separate task for parallelism)
        sync_email_account.delay(str(email_account.id))

    logger.info(f"Triggered sync for {len(email_accounts)} email accounts")


@app.task(bind=True, max_retries=3)
def sync_email_account(self, email_account_id: str):
    """Sync a single email account."""
    db = next(get_db())
    email_account = db.query(EmailAccount).filter(
        EmailAccount.id == email_account_id
    ).first()

    if not email_account:
        logger.error(f"EmailAccount {email_account_id} not found")
        return

    try:
        # Get Gmail service
        gmail_service = get_gmail_service(email_account)

        # Stage 1: Discovery
        last_sync = email_account.last_sync_at or datetime(2020, 1, 1)
        messages = discover_messages(gmail_service, last_sync)

        # Stage 2-4: Fetch, Parse, Normalize
        for message in messages:
            process_message_pipeline(message, gmail_service, email_account, db)

        # Stage 5: Cleanup
        cleanup_old_emails(email_account, db)

        # Update sync status
        email_account.last_sync_at = datetime.utcnow()
        email_account.last_sync_status = 'success'
        db.commit()

        logger.info(f"Sync completed for {email_account_id}: {len(messages)} messages")

    except Exception as e:
        logger.error(f"Sync failed for {email_account_id}: {str(e)}")
        email_account.last_sync_status = 'failed'
        db.commit()

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

---

### Scheduler (Daily Sync)

**File: `backend/app/jobs/scheduler.py`**

```python
from celery.schedules import crontab
from app.jobs.email_sync import sync_all_email_accounts

app.conf.beat_schedule = {
    'sync-emails-daily': {
        'task': 'app.jobs.email_sync.sync_all_email_accounts',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

**Alternative: APScheduler** (if not using Celery):

```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    sync_all_email_accounts,
    'cron',
    hour=2,
    minute=0
)
scheduler.start()
```

---

## Testing Strategy

### Unit Tests

**Test Parsers**:

```python
import pytest
from app.parsers.chase import ChaseParser
from decimal import Decimal

def test_chase_purchase_parsing():
    parser = ChaseParser()
    email = """
    Your Chase Sapphire Reserve card ending in 5678 was used for a
    $12.50 transaction at SQ *BLUE BOTTLE COFFEE on 02/10/2026 at 2:15 PM.
    """

    result = parser.parse(email, subject="Your Chase card was used")

    assert result['merchant_raw'] == 'SQ *BLUE BOTTLE COFFEE'
    assert result['amount'] == Decimal('12.50')
    assert result['payment_instrument_hint'] == '5678'
    assert result['transaction_type'] == 'purchase'
    assert result['confidence_score'] >= 90


def test_chase_refund_parsing():
    parser = ChaseParser()
    email = """
    A refund of $25.00 was processed to your Chase Freedom card
    ending in 1234 from AMAZON.COM.
    """

    result = parser.parse(email, subject="A refund was processed")

    assert result['merchant_raw'] == 'AMAZON.COM'
    assert result['amount'] == Decimal('25.00')
    assert result['transaction_type'] == 'refund'


def test_chase_parser_no_match():
    parser = ChaseParser()
    email = "This is not a transaction email."

    with pytest.raises(ParsingError):
        parser.parse(email, subject="Account update")
```

---

### Integration Tests

**Test End-to-End Pipeline**:

```python
def test_email_sync_pipeline(db_session, mock_gmail_service):
    """Test full pipeline: Gmail → RawEmail → ParsedTransaction → NormalizedTransaction."""
    # Setup: Create EmailAccount
    email_account = create_test_email_account(db_session)

    # Mock Gmail API response
    mock_gmail_service.users().messages().list.return_value.execute.return_value = {
        'messages': [{'id': 'msg-001'}]
    }
    mock_gmail_service.users().messages().get.return_value.execute.return_value = {
        'id': 'msg-001',
        'payload': {
            'headers': [
                {'name': 'Subject', 'value': 'Your Chase card was used'},
                {'name': 'From', 'value': 'no-reply@chase.com'}
            ],
            'body': {
                'data': base64_encode("Your Chase Sapphire Reserve card ending in 5678 was used for a $12.50 transaction at BLUE BOTTLE on 02/10/2026.")
            }
        }
    }

    # Run sync
    sync_email_account(str(email_account.id))

    # Assertions
    raw_emails = db_session.query(RawEmail).filter(RawEmail.email_account_id == email_account.id).all()
    assert len(raw_emails) == 1
    assert raw_emails[0].parsing_status == 'success'

    parsed_txns = db_session.query(ParsedTransaction).filter(ParsedTransaction.user_id == email_account.user_id).all()
    assert len(parsed_txns) == 1
    assert parsed_txns[0].amount == Decimal('12.50')

    normalized_txns = db_session.query(NormalizedTransaction).filter(NormalizedTransaction.user_id == email_account.user_id).all()
    assert len(normalized_txns) == 1
    assert normalized_txns[0].merchant_normalized == 'Blue Bottle Coffee'
```

---

### Test Data

**Sample Emails** (for each issuer):

**File: `backend/tests/fixtures/emails/chase_purchase.txt`**
```
Subject: Your Chase card was used

Your Chase Sapphire Reserve card ending in 5678 was used for a
$12.50 transaction at SQ *BLUE BOTTLE COFFEE on 02/10/2026 at 2:15 PM.

If this wasn't you, let us know immediately.

Thanks,
Chase
```

**File: `backend/tests/fixtures/emails/venmo_sent.txt`**
```
Subject: You paid Sarah Smith $25.00

You paid Sarah Smith $25.00.

February 10, 2026

View on Venmo
```

---

## Document History

| Version | Date       | Author      | Changes                           |
|---------|------------|-------------|-----------------------------------|
| 1.0     | 2026-02-11 | Engineering | Initial email ingestion design    |

---

**Questions? Contact**: engineering@spendi.app