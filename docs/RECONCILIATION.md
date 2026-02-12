# Transaction Reconciliation System: Ledgerly
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Engineering

---

## Overview

The reconciliation system links reimbursement transactions (Venmo receipts, Zelle transfers, Cash App payments) to original purchase transactions without modifying the immutable ledger. This enables users to understand their **net personal spend** while maintaining a complete audit trail of all financial activity.

**Core Principle**: A purchase is always a purchase, even if fully reimbursed. Reimbursements are separate transactions that offset the original cost.

---

## Table of Contents

1. [Data Model](#data-model)
2. [Reconciliation Concepts](#reconciliation-concepts)
3. [Reconciliation Algorithm](#reconciliation-algorithm)
4. [Matching Rules](#matching-rules)
5. [Edge Cases](#edge-cases)
6. [Example Scenarios](#example-scenarios)
7. [UI Display Logic](#ui-display-logic)
8. [Implementation Guide](#implementation-guide)
9. [Testing Strategy](#testing-strategy)

---

## Data Model

### Core Entities

**NormalizedTransaction** (Immutable Ledger)
```sql
CREATE TABLE normalized_transactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    merchant_normalized VARCHAR NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    transaction_date DATE NOT NULL,
    transaction_type VARCHAR NOT NULL,  -- 'purchase', 'refund', 'transfer'

    -- Reimbursement Fields (Computed)
    reimbursement_status VARCHAR DEFAULT 'none',  -- 'none', 'partial', 'full'
    reimbursed_amount NUMERIC(12, 2) DEFAULT 0.00,
    net_amount NUMERIC(12, 2) GENERATED ALWAYS AS (amount - reimbursed_amount) STORED,

    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

**ReimbursementLink** (Many-to-One Relationships)
```sql
CREATE TABLE reimbursement_links (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,

    -- Original Transaction (being reimbursed)
    original_transaction_id UUID NOT NULL REFERENCES normalized_transactions(id),

    -- Reimbursement Transaction (the incoming payment)
    reimbursement_transaction_id UUID REFERENCES normalized_transactions(id),

    -- Reimbursement Details
    reimbursement_amount NUMERIC(12, 2) NOT NULL,
    reimbursement_source VARCHAR NOT NULL,  -- 'Work', 'Friend: John', etc.
    reimbursement_date DATE NOT NULL,

    -- Status
    status VARCHAR DEFAULT 'confirmed',  -- 'expected', 'confirmed', 'cancelled'

    -- Audit
    notes TEXT,
    created_at TIMESTAMP NOT NULL,
    created_by VARCHAR NOT NULL  -- 'user', 'system'
);
```

**Computed Fields (Updated via Trigger)**:
- `NormalizedTransaction.reimbursed_amount` = SUM of all linked `ReimbursementLink.reimbursement_amount` where `status = 'confirmed'`
- `NormalizedTransaction.net_amount` = `amount - reimbursed_amount`
- `NormalizedTransaction.reimbursement_status`:
  - `'none'` if `reimbursed_amount = 0`
  - `'partial'` if `0 < reimbursed_amount < amount`
  - `'full'` if `reimbursed_amount >= amount`

---

## Reconciliation Concepts

### Key Definitions

**Original Transaction (Purchase)**:
- A transaction where the user spent money
- Types: `purchase` (credit card), `transfer` (P2P sent)
- Remains in ledger permanently
- Can have 0-N reimbursements linked to it

**Reimbursement Transaction (Incoming Payment)**:
- A transaction where the user received money
- Types: `transfer` (Venmo received, Zelle received, Cash App received)
- Can be linked to 0-1 original transactions
- One reimbursement can only offset one purchase

**Reimbursement Link**:
- Connects a reimbursement to an original transaction
- Specifies partial amount (if reimbursement covers multiple purchases)
- Immutable once created (preserves audit trail)
- Multiple links can reference the same `original_transaction_id`

---

### Many-to-One Reimbursement Model

**Scenario**: $100 dinner split 4 ways (you pay, 3 friends reimburse you)

```
Original Transaction (Purchase):
┌─────────────────────────────────────────┐
│ ID: txn-001                             │
│ Merchant: Fancy Restaurant              │
│ Amount: $100.00                         │
│ Date: 2026-02-08                        │
│ Type: purchase                          │
│ Reimbursed Amount: $75.00 (computed)    │
│ Net Amount: $25.00 (computed)           │
│ Reimbursement Status: partial           │
└─────────────────────────────────────────┘
                    ▲
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────┴─────┐ ┌───┴──────┐ ┌─┴─────────┐
│ Link 1      │ │ Link 2   │ │ Link 3    │
│ $25.00      │ │ $25.00   │ │ $25.00    │
│ Sarah       │ │ Mike     │ │ Emily     │
│ 2026-02-09  │ │ 02-10    │ │ 02-11     │
└───────┬─────┘ └───┬──────┘ └─┬─────────┘
        │           │           │
        ▼           ▼           ▼
┌─────────────┐ ┌─────────┐ ┌─────────┐
│ Venmo from  │ │ Zelle   │ │ Cash    │
│ Sarah       │ │ from    │ │ App     │
│ $25.00      │ │ Mike    │ │ from    │
│ txn-002     │ │ $25.00  │ │ Emily   │
└─────────────┘ │ txn-003 │ │ $25.00  │
                └─────────┘ │ txn-004 │
                            └─────────┘
```

**Result**:
- Original transaction: $100.00 (unchanged)
- Reimbursed amount: $75.00 (computed from 3 links)
- Net amount: $25.00 (your actual out-of-pocket cost)

---

### Partial Reimbursements

**Scenario**: $50 work lunch, employer reimburses $30 (you pay $20 for personal items)

```
Original Transaction:
- Amount: $50.00
- Reimbursed: $30.00
- Net: $20.00

ReimbursementLink:
- Reimbursement Amount: $30.00 (not full $50)
- Source: "Work expense reimbursement"
```

---

### Unlinked Reimbursements

**Scenario**: Received $50 from John, but forgot which purchase it was for

**Initial State**:
```
Reimbursement Transaction (txn-005):
- Merchant: "Venmo from John"
- Amount: $50.00
- Type: transfer
- (No reimbursement link yet)
```

**User Action**: Manually link to original transaction

**Final State**:
```
ReimbursementLink:
- Original Transaction: txn-001 (dinner at Italian Restaurant, $80.00)
- Reimbursement Transaction: txn-005 (Venmo from John, $50.00)
- Reimbursement Amount: $50.00
- Source: "Friend: John (dinner split)"
- Created By: user
```

---

## Reconciliation Algorithm

### Automatic Matching (System-Generated Links)

**Triggers**:
1. **New reimbursement transaction ingested** (e.g., Venmo received)
2. **User explicitly requests auto-matching** (via UI button)

**Algorithm**: Multi-Pass Scoring with Confidence Threshold

---

### Pass 1: Exact Amount Match (High Confidence)

**Goal**: Find purchases with exact same amount as reimbursement (within date window)

**Matching Criteria**:
- Amount: **Exact match** (e.g., $50.00 = $50.00)
- Date: Within **±7 days** of reimbursement
- Status: Original transaction not already fully reimbursed
- Transaction Type: Original must be `purchase` or `transfer` (sent)

**Confidence Score**: 90-95

**Example**:
```
Original: $50.00 dinner on 2026-02-08
Reimbursement: $50.00 Venmo on 2026-02-10
Match Confidence: 95 (exact amount, within 2 days)
```

**Pseudocode**:
```python
def find_exact_amount_matches(reimbursement: Transaction, date_window_days: int = 7) -> List[Match]:
    date_min = reimbursement.transaction_date - timedelta(days=date_window_days)
    date_max = reimbursement.transaction_date + timedelta(days=date_window_days)

    candidates = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.user_id == reimbursement.user_id,
        NormalizedTransaction.amount == reimbursement.amount,  # Exact match
        NormalizedTransaction.transaction_date.between(date_min, date_max),
        NormalizedTransaction.transaction_type.in_(['purchase', 'transfer']),
        NormalizedTransaction.reimbursement_status != 'full'  # Not already fully reimbursed
    ).all()

    matches = []
    for candidate in candidates:
        days_apart = abs((reimbursement.transaction_date - candidate.transaction_date).days)
        confidence = 95 - (days_apart * 2)  # Reduce 2 points per day apart

        matches.append(Match(
            original_transaction=candidate,
            reimbursement_transaction=reimbursement,
            confidence=confidence,
            match_reason=f"Exact amount match (${reimbursement.amount}), {days_apart} days apart"
        ))

    return sorted(matches, key=lambda m: m.confidence, reverse=True)
```

---

### Pass 2: Merchant + Amount Match (Medium-High Confidence)

**Goal**: Match if reimbursement mentions same merchant as purchase

**Matching Criteria**:
- Amount: **Exact match** OR reimbursement is **factor of original** (e.g., $50 reimb for $100 purchase = 50% split)
- Merchant: Reimbursement merchant contains keywords from original merchant
- Date: Within **±14 days**

**Confidence Score**: 70-85

**Example**:
```
Original: $100.00 at "Blue Bottle Coffee" on 2026-02-08
Reimbursement: $50.00 "Venmo from Sarah (coffee split)" on 2026-02-10
Match: "coffee" keyword found, $50 is 50% of $100
Confidence: 80
```

**Pseudocode**:
```python
def find_merchant_matches(reimbursement: Transaction, date_window_days: int = 14) -> List[Match]:
    # Extract keywords from reimbursement merchant
    keywords = extract_keywords(reimbursement.merchant_normalized)
    # e.g., "Venmo from Sarah (coffee split)" → ["coffee"]

    candidates = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.user_id == reimbursement.user_id,
        NormalizedTransaction.transaction_date.between(date_min, date_max),
        NormalizedTransaction.transaction_type.in_(['purchase', 'transfer']),
        NormalizedTransaction.reimbursement_status != 'full'
    ).all()

    matches = []
    for candidate in candidates:
        # Check if any keyword appears in candidate merchant
        merchant_match = any(kw in candidate.merchant_normalized.lower() for kw in keywords)

        # Check if amount is a factor (e.g., 50% split)
        amount_ratio = reimbursement.amount / candidate.amount
        is_factor = amount_ratio in [0.25, 0.33, 0.5, 0.66, 0.75, 1.0]  # Common split ratios

        if merchant_match and is_factor:
            confidence = 80 if amount_ratio == 1.0 else 75
            matches.append(Match(
                original_transaction=candidate,
                reimbursement_transaction=reimbursement,
                confidence=confidence,
                match_reason=f"Merchant keyword match + amount is {amount_ratio:.0%} of original"
            ))

    return sorted(matches, key=lambda m: m.confidence, reverse=True)
```

---

### Pass 3: Date Proximity + Amount Factor (Low-Medium Confidence)

**Goal**: Match based on timing and common split ratios

**Matching Criteria**:
- Amount: Reimbursement is **common factor** of original (25%, 33%, 50%, 66%, 75%, 100%)
- Date: Within **±3 days** (very close in time)
- No other higher-confidence matches found

**Confidence Score**: 50-65

**Example**:
```
Original: $80.00 dinner on 2026-02-08
Reimbursement: $20.00 Venmo from Mike on 2026-02-09
Match: $20 is 25% of $80 (4-way split), 1 day apart
Confidence: 60
```

---

### Auto-Linking Decision Logic

**Thresholds**:
- **Auto-link (confidence ≥ 85)**: Create `ReimbursementLink` automatically, set `created_by = 'system'`
- **Suggest (confidence 60-84)**: Show suggestion to user in UI ("Possible match: $X purchase at Y on Z")
- **Ignore (confidence < 60)**: Don't suggest (too uncertain)

**Multiple Matches**: If multiple candidates have confidence ≥ 85, **do NOT auto-link** (conflict). Show all candidates to user for manual selection.

**Algorithm Summary**:
```python
def reconcile_reimbursement(reimbursement: Transaction):
    # Run all matching passes
    exact_matches = find_exact_amount_matches(reimbursement)
    merchant_matches = find_merchant_matches(reimbursement)
    proximity_matches = find_proximity_matches(reimbursement)

    # Combine and deduplicate
    all_matches = deduplicate_matches(exact_matches + merchant_matches + proximity_matches)

    # Sort by confidence
    all_matches.sort(key=lambda m: m.confidence, reverse=True)

    # Decision logic
    if not all_matches:
        # No matches found, leave unlinked
        return

    best_match = all_matches[0]

    if best_match.confidence >= 85:
        # Check for conflicts (multiple high-confidence matches)
        high_confidence_matches = [m for m in all_matches if m.confidence >= 85]

        if len(high_confidence_matches) == 1:
            # Auto-link
            create_reimbursement_link(
                original_transaction=best_match.original_transaction,
                reimbursement_transaction=reimbursement,
                amount=reimbursement.amount,
                source=f"Auto-matched: {best_match.match_reason}",
                created_by='system'
            )
        else:
            # Conflict: multiple high-confidence matches
            flag_for_user_review(reimbursement, high_confidence_matches)

    elif best_match.confidence >= 60:
        # Suggest to user
        create_suggested_match(reimbursement, all_matches[:3])  # Top 3 suggestions

    else:
        # Confidence too low, ignore
        pass
```

---

## Matching Rules

### Rule 1: One Reimbursement → One Original Transaction

**Constraint**: A reimbursement transaction can only be linked to **one** original transaction.

**Rationale**: Each incoming payment corresponds to a specific expense.

**Example (Invalid)**:
```
❌ INVALID:
Reimbursement: $50 Venmo from Sarah
- Link 1: $30 to dinner at Restaurant A
- Link 2: $20 to drinks at Bar B

✅ VALID (if Sarah reimbursed for both):
Reimbursement: $50 Venmo from Sarah
- Link 1: $50 to original transaction (split details in notes)
```

**Exception**: If reimbursement covers multiple purchases, user must **manually split** the reimbursement:
1. Create manual transactions for each portion (e.g., "Reimbursement portion 1: $30", "Reimbursement portion 2: $20")
2. Link each portion to respective original transactions

---

### Rule 2: Multiple Reimbursements → One Original Transaction

**Allowed**: An original transaction can have **multiple** reimbursements linked to it.

**Use Case**: Dinner split with 3 friends, each reimburses separately.

**Example**:
```
Original: $100 dinner
- ReimbursementLink 1: $25 from Sarah
- ReimbursementLink 2: $25 from Mike
- ReimbursementLink 3: $50 from Emily (paid double share)
Total Reimbursed: $100
Net: $0
```

---

### Rule 3: Partial Reimbursements Allowed

**Allowed**: Reimbursement amount can be **less than** original transaction amount.

**Use Case**: Work lunch where you ordered personal items.

**Example**:
```
Original: $50 lunch
- ReimbursementLink: $30 from Work
Net: $20 (personal portion)
```

---

### Rule 4: Over-Reimbursement Warning

**Warning**: If `total_reimbursed > original_amount`, flag for user review.

**Possible Reasons**:
- User made a mistake linking
- Reimbursement included tip/tax that wasn't in original email
- Friend paid you back extra by mistake

**Example**:
```
Original: $50 dinner
- ReimbursementLink 1: $30 from Sarah
- ReimbursementLink 2: $30 from Mike
Total Reimbursed: $60
Net: -$10 (over-reimbursed by $10)

⚠️ Warning: "You were reimbursed $10 more than the original transaction. Review linked reimbursements."
```

---

### Rule 5: Immutability of Links

**Constraint**: Once a `ReimbursementLink` is created, it **cannot be modified**.

**Rationale**: Preserve audit trail for financial accuracy.

**To "Undo" a Link**:
1. Set `ReimbursementLink.status = 'cancelled'`
2. Create a new link with corrected details

**Example**:
```
Original Link (Mistake):
- Link ID: link-001
- Original: txn-001 (dinner $100)
- Reimbursement: txn-002 (Venmo $50 from Sarah)
- Status: cancelled

New Link (Corrected):
- Link ID: link-002
- Original: txn-003 (drinks $50)  ← Correct original transaction
- Reimbursement: txn-002 (Venmo $50 from Sarah)
- Status: confirmed
```

---

## Edge Cases

### Edge Case 1: Refunds vs Reimbursements

**Refund**: Return of money from the **same merchant** where you made a purchase.

**Reimbursement**: Payment from a **different person/entity** for an expense you covered.

**Treatment**:
- **Refund**: Creates a new `NormalizedTransaction` with `type = 'refund'`, **not linked** to original purchase (separate transaction)
- **Reimbursement**: Creates a `ReimbursementLink` to original purchase

**Example**:

**Scenario: Refund (Return item to store)**
```
Purchase:
- Date: 2026-02-01
- Merchant: Amazon
- Amount: $50.00
- Type: purchase
- Net: $50.00 (no reimbursement)

Refund (separate transaction):
- Date: 2026-02-10
- Merchant: Amazon (refund)
- Amount: $50.00
- Type: refund
- Net: $50.00

Total Net Spending: $50 - $50 = $0
```

**Scenario: Reimbursement (Friend pays you back)**
```
Purchase:
- Date: 2026-02-01
- Merchant: Amazon
- Amount: $50.00
- Type: purchase
- Reimbursed: $50.00
- Net: $0.00

Reimbursement Transaction:
- Date: 2026-02-05
- Merchant: Venmo from Sarah
- Amount: $50.00
- Type: transfer

ReimbursementLink:
- Original: Purchase (above)
- Reimbursement: Venmo from Sarah
- Amount: $50.00

Total Net Spending: $0 (purchase fully reimbursed)
```

**Why Different?**:
- Refund = You didn't actually spend the money (merchant gave it back)
- Reimbursement = You spent the money, someone else covered it

---

### Edge Case 2: Chargebacks (Fraudulent Transaction)

**Chargeback**: Bank reverses a fraudulent transaction.

**Treatment**: Similar to refund, but with special `transaction_type = 'chargeback'` for clarity.

**Example**:
```
Fraudulent Purchase:
- Date: 2026-02-01
- Merchant: Sketchy Store
- Amount: $200.00
- Type: purchase
- Net: $200.00

Chargeback:
- Date: 2026-03-15 (weeks later)
- Merchant: Sketchy Store (chargeback)
- Amount: $200.00
- Type: chargeback
- Net: $200.00

Total Net: $200 - $200 = $0 (fraud reversed)
```

**Note**: Chargebacks are **not** linked via `ReimbursementLink` (they're separate transactions).

---

### Edge Case 3: Reversals (Pending Transaction Cancelled)

**Reversal**: Transaction was authorized but never settled (e.g., gas station pre-auth for $100, actual charge $50, $50 reversed).

**Treatment**: Mark original transaction as `status = 'reversed'`, create separate reversal transaction.

**Example**:
```
Authorization (Pending):
- Date: 2026-02-01
- Merchant: Shell Gas Station
- Amount: $100.00
- Status: pending

Settlement (Actual Charge):
- Date: 2026-02-03
- Merchant: Shell Gas Station
- Amount: $50.00
- Status: settled

Reversal (System-Generated):
- Date: 2026-02-03
- Merchant: Shell Gas Station (reversal)
- Amount: $50.00
- Type: reversal

Net: Authorization ($100 pending) is cancelled, only $50 settlement counts.
```

**Implementation**: When settlement email arrives, check for pending authorization and mark as reversed.

---

### Edge Case 4: Duplicate Reimbursement (Same Person Pays Twice)

**Scenario**: Sarah sends you $50 twice by mistake for the same expense.

**Detection**:
- Multiple reimbursements from same source (e.g., "Venmo from Sarah") within short time
- Both link to same original transaction

**Treatment**: Flag for user review.

**Example**:
```
Original: $50 dinner

Reimbursement 1:
- Date: 2026-02-09
- Merchant: Venmo from Sarah
- Amount: $50.00
- Linked to original

Reimbursement 2:
- Date: 2026-02-10
- Merchant: Venmo from Sarah
- Amount: $50.00
- System suggests linking to same original

⚠️ Warning: "Sarah already reimbursed $50 for this purchase. Is this a duplicate?"
```

---

### Edge Case 5: Expected Reimbursements (Not Yet Received)

**Scenario**: You paid $100 for dinner, Sarah owes you $50 but hasn't paid yet.

**Treatment**: Create `ReimbursementLink` with `status = 'expected'` and `reimbursement_transaction_id = NULL`.

**Example**:
```
Original: $100 dinner on 2026-02-08

Expected Reimbursement (User-Created):
- Original Transaction: txn-001 (dinner)
- Reimbursement Transaction: NULL (not received yet)
- Reimbursement Amount: $50.00
- Source: "Friend: Sarah (pending)"
- Status: expected
- Date: 2026-02-15 (expected date)

Computed Fields:
- Reimbursed Amount: $0.00 (only 'confirmed' status counts)
- Net: $100.00 (full amount until received)
```

**When Payment Received**:
1. Venmo from Sarah arrives ($50)
2. System suggests linking to expected reimbursement
3. User confirms
4. Update link: `reimbursement_transaction_id = txn-002`, `status = 'confirmed'`
5. Recompute: `reimbursed_amount = $50`, `net = $50`

---

## Example Scenarios

### Scenario 1: Simple Full Reimbursement

**Setup**:
- You paid $50 for lunch
- Your friend reimburses you $50 via Venmo

**Transactions**:
```
txn-001 (Original Purchase):
- Date: 2026-02-08
- Merchant: Blue Bottle Coffee
- Amount: $50.00
- Type: purchase
- Payment Instrument: Chase Sapphire Reserve (5678)

txn-002 (Reimbursement):
- Date: 2026-02-10
- Merchant: Venmo from Sarah
- Amount: $50.00
- Type: transfer
- Payment Instrument: Venmo
```

**Reconciliation**:
```
System auto-matches (confidence 95):
- Exact amount: $50.00 = $50.00 ✓
- Date within 7 days: 2 days apart ✓
- Not already fully reimbursed ✓

Creates ReimbursementLink:
- ID: link-001
- Original Transaction: txn-001
- Reimbursement Transaction: txn-002
- Reimbursement Amount: $50.00
- Source: "Auto-matched: Exact amount match ($50.00), 2 days apart"
- Status: confirmed
- Created By: system
```

**Computed Results**:
```
txn-001 (Updated):
- Reimbursed Amount: $50.00
- Net Amount: $0.00
- Reimbursement Status: full
```

**UI Display**:
```
┌──────────────────────────────────────────────────────────┐
│ Blue Bottle Coffee                                       │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $50.00                           │
│ Reimbursements:         $50.00                           │
│   ✓ Venmo from Sarah    $50.00  (Feb 10)                │
│ ─────────────────────────────────                        │
│ Net Cost:               $0.00                            │
└──────────────────────────────────────────────────────────┘
```

---

### Scenario 2: Dinner Split 4 Ways (Multiple Reimbursements)

**Setup**:
- You paid $100 for dinner
- 3 friends each owe you $25

**Transactions**:
```
txn-001 (Original Purchase):
- Date: 2026-02-08
- Merchant: Fancy Restaurant
- Amount: $100.00

txn-002 (Reimbursement from Sarah):
- Date: 2026-02-09
- Merchant: Venmo from Sarah
- Amount: $25.00

txn-003 (Reimbursement from Mike):
- Date: 2026-02-10
- Merchant: Zelle from Mike
- Amount: $25.00

txn-004 (Reimbursement from Emily):
- Date: 2026-02-11
- Merchant: Cash App from Emily
- Amount: $25.00
```

**Reconciliation**:
```
For txn-002:
- System suggests match (confidence 75): Amount is 25% of $100, 1 day apart
- User confirms and links to txn-001
- ReimbursementLink-1 created: $25.00 from Sarah

For txn-003:
- System suggests match (confidence 70): Amount is 25% of $100, 2 days apart
- User confirms and links to txn-001
- ReimbursementLink-2 created: $25.00 from Mike

For txn-004:
- System suggests match (confidence 65): Amount is 25% of $100, 3 days apart
- User confirms and links to txn-001
- ReimbursementLink-3 created: $25.00 from Emily
```

**Computed Results (After All 3 Links)**:
```
txn-001 (Updated):
- Reimbursed Amount: $75.00  (3 × $25)
- Net Amount: $25.00
- Reimbursement Status: partial
```

**UI Display**:
```
┌──────────────────────────────────────────────────────────┐
│ Fancy Restaurant                                         │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $100.00                          │
│ Reimbursements:         $75.00                           │
│   ✓ Venmo from Sarah    $25.00  (Feb 9)                 │
│   ✓ Zelle from Mike     $25.00  (Feb 10)                │
│   ✓ Cash App from Emily $25.00  (Feb 11)                │
│ ─────────────────────────────────                        │
│ Net Cost:               $25.00                           │
│                                                          │
│ Your share: 25% of total                                 │
└──────────────────────────────────────────────────────────┘
```

---

### Scenario 3: Partial Reimbursement (Work Expense)

**Setup**:
- You paid $80 for lunch with coworker
- $50 was work-related (billable), $30 was personal
- Work reimburses $50

**Transactions**:
```
txn-001 (Original Purchase):
- Date: 2026-02-08
- Merchant: The Capital Grille
- Amount: $80.00

txn-002 (Work Reimbursement):
- Date: 2026-02-15
- Merchant: Expense Reimbursement (manual entry)
- Amount: $50.00
- Type: transfer
```

**Reconciliation**:
```
User manually links:
- Original Transaction: txn-001
- Reimbursement Transaction: txn-002
- Reimbursement Amount: $50.00
- Source: "Work expense reimbursement (client lunch)"
- Notes: "Personal items: $30 (drinks and dessert)"
- Created By: user
```

**Computed Results**:
```
txn-001 (Updated):
- Reimbursed Amount: $50.00
- Net Amount: $30.00
- Reimbursement Status: partial
```

**UI Display**:
```
┌──────────────────────────────────────────────────────────┐
│ The Capital Grille                                       │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $80.00                           │
│ Reimbursements:         $50.00                           │
│   ✓ Work expense        $50.00  (Feb 15)                │
│     reimbursement                                        │
│     Note: Personal items: $30 (drinks and dessert)      │
│ ─────────────────────────────────                        │
│ Net Cost:               $30.00                           │
│                                                          │
│ Reimbursed: 62.5% • Personal: 37.5%                     │
└──────────────────────────────────────────────────────────┘
```

---

### Scenario 4: Unlinked Reimbursement (Manual Linking Required)

**Setup**:
- You paid for multiple things last week
- Friend sends you $35 via Venmo with note "for the other day"
- You can't remember which purchase it was for

**Transactions**:
```
txn-001:
- Date: 2026-02-05
- Merchant: Movie Theater
- Amount: $30.00

txn-002:
- Date: 2026-02-06
- Merchant: Coffee Shop
- Amount: $15.00

txn-003:
- Date: 2026-02-07
- Merchant: Lunch Spot
- Amount: $35.00

txn-004 (Reimbursement):
- Date: 2026-02-10
- Merchant: Venmo from John
- Amount: $35.00
```

**Reconciliation**:
```
System finds matches:
- txn-001: Confidence 55 (amount mismatch)
- txn-002: Confidence 50 (amount mismatch)
- txn-003: Confidence 90 (exact amount, 3 days apart)

System suggests txn-003 (lunch, $35) as best match.
```

**UI Suggestion**:
```
┌──────────────────────────────────────────────────────────┐
│ Unlinked Reimbursement                                   │
│ Venmo from John                                          │
│ Feb 10, 2026 • $35.00                                    │
├──────────────────────────────────────────────────────────┤
│ 💡 Suggested Match (90% confident):                      │
│                                                          │
│ Lunch Spot                                               │
│ Feb 7, 2026 • $35.00                                     │
│                                                          │
│ [Link to This Purchase]  [Choose Different]  [Skip]     │
└──────────────────────────────────────────────────────────┘
```

**User Confirms → Link Created**

---

### Scenario 5: Over-Reimbursement Warning

**Setup**:
- You paid $60 for dinner
- Friend accidentally sends you $70 (typo)

**Transactions**:
```
txn-001 (Original):
- Merchant: Italian Restaurant
- Amount: $60.00

txn-002 (Reimbursement):
- Merchant: Venmo from Sarah
- Amount: $70.00
```

**Reconciliation**:
```
System auto-links (confidence 85):
- Similar amount (within 20%)
- 2 days apart

ReimbursementLink created:
- Amount: $70.00 (full reimbursement amount)

Computed:
- Reimbursed Amount: $70.00
- Net Amount: -$10.00 (over-reimbursed)
- Reimbursement Status: full
```

**UI Warning**:
```
┌──────────────────────────────────────────────────────────┐
│ Italian Restaurant                                       │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $60.00                           │
│ Reimbursements:         $70.00                           │
│   ✓ Venmo from Sarah    $70.00  (Feb 10)                │
│ ──────────���──────────────────────                        │
│ Net Cost:               -$10.00                          │
│                                                          │
│ ⚠️ You were reimbursed $10 more than the purchase.      │
│    This may be a mistake.                                │
│                                                          │
│ [Review Link]  [Unlink]  [Keep As-Is]                   │
└──────────────────────────────────────────────────────────┘
```

---

### Scenario 6: Expected Reimbursement (Not Yet Received)

**Setup**:
- You paid $100 for concert tickets for you and Sarah
- Sarah owes you $50 but hasn't paid yet
- You want to track this pending reimbursement

**Transactions**:
```
txn-001 (Original):
- Date: 2026-02-08
- Merchant: Ticketmaster
- Amount: $100.00
```

**User Action**: Mark as "Expected Reimbursement"

**Reconciliation**:
```
User creates expected reimbursement:
- Original Transaction: txn-001
- Reimbursement Transaction: NULL (not received yet)
- Reimbursement Amount: $50.00
- Source: "Friend: Sarah (concert ticket split)"
- Status: expected
- Expected Date: 2026-02-20
- Created By: user

Computed (Expected reimbursements don't count until confirmed):
- Reimbursed Amount: $0.00
- Net Amount: $100.00 (full amount)
- Reimbursement Status: none
```

**UI Display**:
```
┌──────────────────────────────────────────────────────────┐
│ Ticketmaster                                             │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $100.00                          │
│ Expected Reimbursements:                                 │
│   ⏳ Sarah (concert)    $50.00  (Expected: Feb 20)       │
│ ─────────────────────────────────                        │
│ Current Net Cost:       $100.00                          │
│ Net After Expected:     $50.00                           │
└──────────────────────────────────────────────────────────┘
```

**When Sarah Pays**:
```
txn-002 (Reimbursement):
- Date: 2026-02-18
- Merchant: Venmo from Sarah
- Amount: $50.00

System matches to expected reimbursement (confidence 95):
- Amount matches: $50.00 = $50.00
- Source matches: "Sarah"
- Within expected timeframe

System updates link:
- Reimbursement Transaction: txn-002 (was NULL)
- Status: confirmed (was expected)

Computed (Now counts):
- Reimbursed Amount: $50.00
- Net Amount: $50.00
- Reimbursement Status: partial
```

---

## UI Display Logic

### Transaction List View

**Display Rules**:
1. Show **all transactions** (purchases, reimbursements, refunds)
2. Use visual indicators for reimbursement status:
   - 🟢 Green: Fully reimbursed
   - 🟡 Yellow: Partially reimbursed
   - ⏳ Gray: Expected reimbursement pending
   - 🔴 Red: No reimbursement (normal)

**Example List**:
```
┌─────────────────────────────────────────────────────────┐
│ February 2026 Transactions                              │
├─────────────────────────────────────────────────────────┤
│ Feb 10 • Venmo from Sarah          +$50.00             │
│          [Linked to Blue Bottle]                        │
│                                                         │
│ Feb 9  • 🟢 Blue Bottle Coffee      $50.00   Net: $0   │
│          Reimbursed by Sarah                            │
│                                                         │
│ Feb 8  • 🟡 Fancy Restaurant       $100.00  Net: $25   │
│          Partially reimbursed (75%)                     │
│                                                         │
│ Feb 7  • 🔴 Grocery Store           $75.00             │
│                                                         │
│ Feb 6  • ⏳ Concert Tickets        $100.00  Net: $100  │
│          Expecting $50 from Sarah                       │
└─────────────────────────────────────────────────────────┘
```

---

### Transaction Detail View

**Sections**:
1. **Transaction Info**: Merchant, date, amount, card
2. **Reimbursements**: List all linked reimbursements
3. **Net Calculation**: Visual breakdown of net cost
4. **Actions**: Link reimbursement, add expected reimbursement

**Example**:
```
┌──────────────────────────────────────────────────────────┐
│ Transaction Details                                      │
├──────────────────────────────────────────────────────────┤
│ Fancy Restaurant                                         │
│ February 8, 2026 at 7:30 PM                              │
│ Chase Sapphire Reserve (••5678)                          │
│ Category: Dining                                         │
│                                                          │
│ ─────────────────────────────────                        │
│ Purchase Amount                             $100.00      │
│ ─────────────────────────────────                        │
│                                                          │
│ Reimbursements                                           │
│ ✓ Venmo from Sarah             $25.00   Feb 9           │
│ ✓ Zelle from Mike              $25.00   Feb 10          │
│ ✓ Cash App from Emily          $25.00   Feb 11          │
│ ─────────────────────────────────                        │
│ Total Reimbursed                            $75.00       │
│                                                          │
│ ═════════════════════════════════                        │
│ Net Personal Cost                           $25.00       │
│ ═════════════════════════════════                        │
│                                                          │
│ [+ Link Reimbursement]  [+ Add Expected]                │
│                                                          │
│ Notes:                                                   │
│ Dinner split 4 ways                                      │
│                                                          │
│ ─────────────────────────────────                        │
│ Rewards Earned: 300 points (3× dining)                  │
└──────────────────────────────────────────────────────────┘
```

---

### Spending Summary Dashboard

**Net Spending Calculation**:
```
Gross Spending: Sum of all purchases
Total Reimbursed: Sum of all reimbursed_amount
Net Spending: Gross - Total Reimbursed
```

**Example**:
```
┌──────────────────────────────────────────────────────────┐
│ February 2026 Summary                                    │
├──────────────────────────────────────────────────────────┤
│ Gross Spending               $2,450.00                   │
│ Total Reimbursed             $  450.00                   │
│ ───────────────────────────────────────                  │
│ Net Personal Spending        $2,000.00                   │
│                                                          │
│ By Category (Net):                                       │
│ • Dining           $  500.00  (was $700, $200 reimbursed)│
│ • Groceries        $  300.00  (no reimbursements)        │
│ • Transportation   $  150.00  (was $300, $150 reimbursed)│
│ • Entertainment    $  250.00  (was $350, $100 reimbursed)│
│ • Other            $  800.00  (no reimbursements)        │
└──────────────────────────────────────────────────────────┘
```

---

## Implementation Guide

### Database Trigger: Update Reimbursed Amount

**File: `backend/alembic/versions/xxx_add_reimbursement_trigger.py`**

```sql
-- Trigger to recompute reimbursed_amount when ReimbursementLink changes
CREATE OR REPLACE FUNCTION update_reimbursed_amount()
RETURNS TRIGGER AS $$
BEGIN
    -- Recompute reimbursed_amount for affected original transaction
    UPDATE normalized_transactions
    SET
        reimbursed_amount = (
            SELECT COALESCE(SUM(reimbursement_amount), 0)
            FROM reimbursement_links
            WHERE original_transaction_id = NEW.original_transaction_id
              AND status = 'confirmed'
        ),
        updated_at = NOW()
    WHERE id = NEW.original_transaction_id;

    -- Update reimbursement status
    UPDATE normalized_transactions
    SET reimbursement_status = CASE
        WHEN reimbursed_amount = 0 THEN 'none'
        WHEN reimbursed_amount >= amount THEN 'full'
        ELSE 'partial'
    END
    WHERE id = NEW.original_transaction_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reimbursement_link_changed
AFTER INSERT OR UPDATE OR DELETE ON reimbursement_links
FOR EACH ROW
EXECUTE FUNCTION update_reimbursed_amount();
```

---

### API Endpoints

**File: `backend/app/reconciliation/routes.py`**

```python
from fastapi import APIRouter, HTTPException, Depends
from app.db.session import get_db
from app.db.models import NormalizedTransaction, ReimbursementLink
from app.auth.middleware import get_current_user
from app.reconciliation.matcher import find_matches

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

# ============================================================================
# Get Suggested Matches for Reimbursement
# ============================================================================

@router.get("/reimbursements/{transaction_id}/matches")
def get_suggested_matches(
    transaction_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get suggested original transactions to link to this reimbursement."""
    # Verify transaction belongs to user
    reimbursement = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.user_id == current_user.id,
        NormalizedTransaction.transaction_type == 'transfer'
    ).first()

    if not reimbursement:
        raise HTTPException(status_code=404, detail="Reimbursement not found")

    # Find matches
    matches = find_matches(reimbursement, db)

    return {
        "reimbursement": {
            "id": str(reimbursement.id),
            "merchant": reimbursement.merchant_normalized,
            "amount": float(reimbursement.amount),
            "date": reimbursement.transaction_date.isoformat()
        },
        "suggested_matches": [
            {
                "transaction_id": str(m.original_transaction.id),
                "merchant": m.original_transaction.merchant_normalized,
                "amount": float(m.original_transaction.amount),
                "date": m.original_transaction.transaction_date.isoformat(),
                "confidence": m.confidence,
                "match_reason": m.match_reason
            }
            for m in matches[:5]  # Top 5 matches
        ]
    }


# ============================================================================
# Create Reimbursement Link (Manual or Confirmed Suggestion)
# ============================================================================

@router.post("/reimbursements/{reimbursement_id}/link")
def link_reimbursement(
    reimbursement_id: str,
    link_data: dict,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Link a reimbursement to an original transaction."""
    # Verify transactions belong to user
    reimbursement = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == reimbursement_id,
        NormalizedTransaction.user_id == current_user.id
    ).first()

    original = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == link_data['original_transaction_id'],
        NormalizedTransaction.user_id == current_user.id
    ).first()

    if not reimbursement or not original:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Validate
    if reimbursement.transaction_type != 'transfer':
        raise HTTPException(status_code=400, detail="Reimbursement must be a transfer")

    if original.transaction_type not in ['purchase', 'transfer']:
        raise HTTPException(status_code=400, detail="Original must be a purchase or transfer")

    # Create link
    link = ReimbursementLink(
        user_id=current_user.id,
        original_transaction_id=original.id,
        reimbursement_transaction_id=reimbursement.id,
        reimbursement_amount=link_data.get('amount', reimbursement.amount),
        reimbursement_source=link_data.get('source', f"From {reimbursement.merchant_normalized}"),
        reimbursement_date=reimbursement.transaction_date,
        status='confirmed',
        notes=link_data.get('notes'),
        created_by='user'
    )

    db.add(link)
    db.commit()

    # Trigger will auto-update reimbursed_amount

    return {"message": "Reimbursement linked successfully", "link_id": str(link.id)}


# ============================================================================
# Add Expected Reimbursement (Not Yet Received)
# ============================================================================

@router.post("/transactions/{transaction_id}/expected-reimbursement")
def add_expected_reimbursement(
    transaction_id: str,
    expected_data: dict,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Mark a transaction as having an expected reimbursement."""
    original = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.user_id == current_user.id
    ).first()

    if not original:
        raise HTTPException(status_code=404, detail="Transaction not found")

    link = ReimbursementLink(
        user_id=current_user.id,
        original_transaction_id=original.id,
        reimbursement_transaction_id=None,  # Not received yet
        reimbursement_amount=expected_data['amount'],
        reimbursement_source=expected_data['source'],
        reimbursement_date=expected_data['expected_date'],
        status='expected',
        notes=expected_data.get('notes'),
        created_by='user'
    )

    db.add(link)
    db.commit()

    return {"message": "Expected reimbursement added", "link_id": str(link.id)}
```

---

## Testing Strategy

### Unit Tests: Matching Algorithm

```python
import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.reconciliation.matcher import find_exact_amount_matches, find_merchant_matches

def test_exact_amount_match(db_session):
    """Test exact amount matching within date window."""
    # Setup: Create original transaction
    original = NormalizedTransaction(
        user_id=user.id,
        merchant_normalized="Blue Bottle Coffee",
        amount=Decimal('50.00'),
        transaction_date=date(2026, 2, 8),
        transaction_type='purchase'
    )
    db_session.add(original)

    # Create reimbursement
    reimbursement = NormalizedTransaction(
        user_id=user.id,
        merchant_normalized="Venmo from Sarah",
        amount=Decimal('50.00'),
        transaction_date=date(2026, 2, 10),  # 2 days later
        transaction_type='transfer'
    )
    db_session.add(reimbursement)
    db_session.commit()

    # Test matching
    matches = find_exact_amount_matches(reimbursement, db_session)

    assert len(matches) == 1
    assert matches[0].original_transaction.id == original.id
    assert matches[0].confidence >= 90


def test_no_match_outside_date_window(db_session):
    """Test that matches outside date window are not returned."""
    original = create_transaction(amount=50.00, date=date(2026, 2, 1))
    reimbursement = create_transaction(amount=50.00, date=date(2026, 2, 20))  # 19 days later

    matches = find_exact_amount_matches(reimbursement, db_session, date_window_days=7)

    assert len(matches) == 0  # Outside 7-day window


def test_partial_reimbursement_matching(db_session):
    """Test matching partial reimbursement (25% split)."""
    original = create_transaction(amount=100.00, date=date(2026, 2, 8))
    reimbursement = create_transaction(amount=25.00, date=date(2026, 2, 10))

    matches = find_merchant_matches(reimbursement, db_session)

    assert len(matches) > 0
    assert matches[0].confidence >= 60  # Lower confidence for partial
```

---

### Integration Tests: Full Reconciliation Flow

```python
def test_auto_linking_flow(db_session):
    """Test automatic linking when confidence is high."""
    # Setup
    original = create_purchase(amount=50.00, date=date(2026, 2, 8))
    reimbursement = create_transfer(amount=50.00, date=date(2026, 2, 10))

    # Trigger reconciliation
    from app.reconciliation.engine import reconcile_reimbursement
    reconcile_reimbursement(reimbursement)

    # Assertions
    links = db_session.query(ReimbursementLink).filter(
        ReimbursementLink.original_transaction_id == original.id
    ).all()

    assert len(links) == 1
    assert links[0].status == 'confirmed'
    assert links[0].created_by == 'system'

    # Check computed fields
    db_session.refresh(original)
    assert original.reimbursed_amount == Decimal('50.00')
    assert original.net_amount == Decimal('0.00')
    assert original.reimbursement_status == 'full'
```

---

## Document History

| Version | Date       | Author      | Changes                              |
|---------|------------|-------------|--------------------------------------|
| 1.0     | 2026-02-11 | Engineering | Initial reconciliation system design |

---

**Questions? Contact**: engineering@ledgerly.app