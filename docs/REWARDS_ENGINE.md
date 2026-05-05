# Credit Card Rewards Engine: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Engineering

---

## Overview

The rewards engine calculates credit card points and cashback earned for each transaction based on card-specific rules and time-bound promotions. The system is designed to be:

1. **Explainable**: Every point calculation shows the formula and reasoning
2. **Accurate**: Uses decimal precision (no float arithmetic)
3. **Auditable**: Immutable PointsTransaction records with calculation trail
4. **Flexible**: Supports time-bound promotions, category overrides, manual adjustments

**Key Principle**: Rewards are earned when a purchase is made, not when it's reimbursed. Reimbursements do NOT claw back points (you keep the points even if expense was reimbursed).

---

## Table of Contents

1. [Storage Model](#storage-model)
2. [Rule Engine Architecture](#rule-engine-architecture)
3. [Category Inference](#category-inference)
4. [Rewards Calculation](#rewards-calculation)
5. [Time-Bound Promotions](#time-bound-promotions)
6. [Manual Overrides](#manual-overrides)
7. [Points Lifecycle](#points-lifecycle)
8. [Reimbursement Handling](#reimbursement-handling)
9. [Example Calculations](#example-calculations)
10. [Implementation Guide](#implementation-guide)

---

## Storage Model

### Core Entities

**PaymentInstrument** (Credit Cards)
```sql
CREATE TABLE payment_instruments (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    type VARCHAR NOT NULL,  -- 'credit_card', 'debit_card', 'p2p_account'
    issuer VARCHAR NOT NULL,  -- 'chase', 'amex', 'citi', etc.
    display_name VARCHAR NOT NULL,
    last_four_digits VARCHAR(4),
    network VARCHAR,  -- 'visa', 'mastercard', 'amex', 'discover'
    status VARCHAR DEFAULT 'active'
);
```

**RewardsProfile** (Card Reward Rules)
```sql
CREATE TABLE rewards_profiles (
    id UUID PRIMARY KEY,
    payment_instrument_id UUID NOT NULL REFERENCES payment_instruments(id),
    user_id UUID NOT NULL,

    -- Profile Metadata
    profile_name VARCHAR NOT NULL,  -- 'Chase Sapphire Reserve - Standard'
    valid_from DATE NOT NULL,
    valid_until DATE,  -- NULL = ongoing

    -- Default Rate
    default_rate NUMERIC(5, 2) NOT NULL,  -- e.g., 1.0 = 1% or 1 point per dollar
    rate_type VARCHAR NOT NULL,  -- 'cashback_percent', 'points_per_dollar'

    -- Category-Specific Rates (JSONB)
    category_rates JSONB NOT NULL,  -- {"dining": 3.0, "travel": 3.0, ...}

    -- Card Details
    annual_fee NUMERIC(8, 2) DEFAULT 0.00,
    signup_bonus NUMERIC(10, 2),  -- e.g., 60000 points

    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Example category_rates:
-- {
--   "dining": 3.0,
--   "travel": 3.0,
--   "groceries": 1.0,
--   "gas": 1.0,
--   "other": 1.0
-- }
```

**PointsTransaction** (Immutable Rewards Record)
```sql
CREATE TABLE points_transactions (
    id UUID PRIMARY KEY,
    normalized_transaction_id UUID NOT NULL REFERENCES normalized_transactions(id) UNIQUE,
    rewards_profile_id UUID NOT NULL REFERENCES rewards_profiles(id),
    user_id UUID NOT NULL,

    -- Calculation Details
    points_earned NUMERIC(12, 2) NOT NULL,
    rate_applied NUMERIC(5, 2) NOT NULL,  -- e.g., 3.0
    category_used VARCHAR NOT NULL,  -- e.g., 'dining'
    rate_type VARCHAR NOT NULL,  -- 'cashback_percent', 'points_per_dollar'

    -- Explainability
    calculation_formula VARCHAR NOT NULL,  -- e.g., '$50.00 × 3.0 points/dollar = 150 points'

    -- Lifecycle
    status VARCHAR DEFAULT 'earned',  -- 'earned', 'pending', 'redeemed', 'expired'

    created_at TIMESTAMP NOT NULL
);
```

**PointsRedemption** (Optional: Track Point Redemptions)
```sql
CREATE TABLE points_redemptions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    payment_instrument_id UUID NOT NULL,

    -- Redemption Details
    points_redeemed NUMERIC(12, 2) NOT NULL,
    redemption_value NUMERIC(12, 2),  -- Dollar value (e.g., $150 for 10,000 points)
    redemption_date DATE NOT NULL,
    redemption_type VARCHAR NOT NULL,  -- 'statement_credit', 'travel', 'gift_card', 'transfer'
    notes TEXT,

    created_at TIMESTAMP NOT NULL
);
```

---

## Rule Engine Architecture

### Three-Layer Rule Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Manual Override (Highest Priority)            │
│ - User manually sets reward rate for specific txn      │
│ - Example: "This was actually 5% back, not 1%"         │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Time-Bound Promotion (Medium Priority)        │
│ - Card has active promotion for date range             │
│ - Example: Q1 2026 = 5% on groceries (Discover It)     │
└─────────────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Standard Rate (Lowest Priority)               │
│ - Card's base reward rate by category                  │
│ - Example: 3% dining, 1% everything else (Chase)       │
└─────────────────────────────────────────────────────────┘
```

---

### Rule Selection Algorithm

**Pseudocode**:
```python
def get_applicable_rate(transaction: NormalizedTransaction) -> RewardRate:
    # Layer 3: Check for manual override
    override = db.query(PointsOverride).filter(
        PointsOverride.transaction_id == transaction.id
    ).first()
    if override:
        return RewardRate(
            rate=override.rate,
            category=override.category,
            source='manual_override',
            reason=override.reason
        )

    # Layer 2: Check for time-bound promotion
    promotion = db.query(RewardsProfile).filter(
        RewardsProfile.payment_instrument_id == transaction.payment_instrument_id,
        RewardsProfile.valid_from <= transaction.transaction_date,
        RewardsProfile.valid_until >= transaction.transaction_date,
        RewardsProfile.is_promotion == True  # Special flag for promotions
    ).first()
    if promotion:
        category_rate = promotion.category_rates.get(transaction.category, promotion.default_rate)
        return RewardRate(
            rate=category_rate,
            category=transaction.category,
            source='time_bound_promotion',
            reason=f"{promotion.profile_name}"
        )

    # Layer 1: Use standard rewards profile
    standard_profile = db.query(RewardsProfile).filter(
        RewardsProfile.payment_instrument_id == transaction.payment_instrument_id,
        RewardsProfile.valid_from <= transaction.transaction_date,
        (RewardsProfile.valid_until.is_(None) | (RewardsProfile.valid_until >= transaction.transaction_date)),
        RewardsProfile.is_promotion == False
    ).first()

    if standard_profile:
        category_rate = standard_profile.category_rates.get(transaction.category, standard_profile.default_rate)
        return RewardRate(
            rate=category_rate,
            category=transaction.category,
            source='standard_rate',
            reason=f"{standard_profile.profile_name}"
        )

    # No rate found (debit card or unknown card)
    return RewardRate(rate=0, category='other', source='no_rewards', reason='Card has no rewards program')
```

---

## Category Inference

### Problem: How to Assign Categories to Transactions?

**Challenge**: Merchant names don't always indicate category (e.g., "Amazon" sells everything).

**Solution**: Multi-Tier Category Inference

---

### Tier 1: Rule-Based Merchant Mapping (High Confidence)

**Known Merchant → Category Mapping**:
```python
MERCHANT_CATEGORY_MAP = {
    # Dining
    'starbucks': 'dining',
    'chipotle': 'dining',
    'mcdonald': 'dining',
    'panera': 'dining',
    'blue bottle': 'dining',

    # Groceries
    'whole foods': 'groceries',
    'trader joe': 'groceries',
    'safeway': 'groceries',
    'kroger': 'groceries',
    'costco': 'groceries',

    # Gas
    'shell': 'gas',
    'chevron': 'gas',
    'exxon': 'gas',
    'bp': 'gas',

    # Travel
    'united airlines': 'travel',
    'delta': 'travel',
    'marriott': 'travel',
    'hilton': 'travel',
    'uber': 'travel',
    'lyft': 'travel',

    # Entertainment
    'netflix': 'entertainment',
    'spotify': 'entertainment',
    'amc theaters': 'entertainment',

    # Other
    'amazon': 'shopping',  # Default to shopping (could be anything)
    'target': 'shopping',
    'walmart': 'shopping'
}

def infer_category_from_merchant(merchant: str) -> Optional[str]:
    """Fuzzy match merchant to known category."""
    merchant_lower = merchant.lower()
    for keyword, category in MERCHANT_CATEGORY_MAP.items():
        if keyword in merchant_lower:
            return category
    return None
```

**Confidence**: 90-95% (known merchants)

---

### Tier 2: MCC Code Mapping (Medium-High Confidence)

**Merchant Category Code (MCC)**: 4-digit code assigned by card networks

**Common MCC → Category Mapping**:
```python
MCC_CATEGORY_MAP = {
    # Dining (5812, 5814)
    '5812': 'dining',  # Eating Places, Restaurants
    '5814': 'dining',  # Fast Food Restaurants

    # Groceries (5411)
    '5411': 'groceries',  # Grocery Stores, Supermarkets

    # Gas (5541, 5542)
    '5541': 'gas',  # Service Stations (with or without ancillary services)
    '5542': 'gas',  # Automated Fuel Dispensers

    # Travel (3000-3299, 4511, 4722)
    '3000': 'travel',  # Airlines
    '3001': 'travel',  # United Airlines
    '4511': 'travel',  # Airlines, Air Carriers
    '4722': 'travel',  # Travel Agencies

    # Hotels (3501-3999, 7011)
    '7011': 'travel',  # Hotels, Motels, Resorts

    # Entertainment (5816, 7832, 7922)
    '5816': 'entertainment',  # Digital Goods: Games
    '7832': 'entertainment',  # Motion Picture Theaters
    '7922': 'entertainment',  # Theatrical Producers (Except Motion Pictures)

    # Shopping (5310, 5331, 5399)
    '5310': 'shopping',  # Discount Stores
    '5331': 'shopping',  # Variety Stores
    '5399': 'shopping',  # Miscellaneous General Merchandise
}
```

**Limitation**: MCC codes are NOT always included in transaction emails (depends on issuer).

**If MCC Available**: Use MCC mapping (95% confidence)

**Confidence**: 85-90% (if MCC available)

---

### Tier 3: Machine Learning (Medium Confidence)

**Approach**: Train classifier on labeled transaction data

**Features**:
- Merchant name (TF-IDF vectorized)
- Transaction amount
- Day of week / time of day
- User's historical categorization patterns

**Training Data**:
- User-corrected categories (ground truth)
- Community-labeled merchants (crowdsourced)

**Model**: Logistic Regression or Random Forest

**Output**: Category + confidence score

**Confidence**: 70-85%

---

### Tier 4: LLM-Based Inference (Last Resort)

**Approach**: Use GPT-4 to infer category from merchant name

**Example Prompt**:
```
Categorize this transaction into one of these categories:
- dining
- groceries
- gas
- travel
- entertainment
- shopping
- utilities
- healthcare
- other

Transaction: "SQ *BLUE BOTTLE COFFEE"
Amount: $12.50
Date: 2026-02-10

Return only the category name.
```

**Output**: `dining`

**Confidence**: 75-85% (may hallucinate for ambiguous merchants)

**Cost**: $0.0001 per transaction (expensive at scale)

---

### Category Inference Pipeline

```python
def infer_category(transaction: NormalizedTransaction) -> Tuple[str, int]:
    """
    Infer category for transaction.

    Returns:
        (category, confidence_score)
    """
    # Tier 1: Rule-based merchant mapping
    category = infer_category_from_merchant(transaction.merchant_normalized)
    if category:
        return (category, 95)

    # Tier 2: MCC code (if available)
    if transaction.mcc_code:
        category = MCC_CATEGORY_MAP.get(transaction.mcc_code)
        if category:
            return (category, 90)

    # Tier 3: ML model
    category, confidence = ml_model.predict(transaction)
    if confidence >= 70:
        return (category, confidence)

    # Tier 4: LLM (fallback)
    category = llm_infer_category(transaction)
    return (category, 75)  # Moderate confidence

    # Default: 'other'
    return ('other', 50)
```

---

## Rewards Calculation

### Calculation Formula

**Points Per Dollar**:
```
points_earned = transaction.amount × rate
```

**Cashback Percent**:
```
cashback_earned = transaction.amount × (rate / 100)
```

---

### Calculation Engine

```python
from decimal import Decimal

def calculate_rewards(transaction: NormalizedTransaction) -> PointsTransaction:
    """
    Calculate rewards for a transaction.

    Returns:
        PointsTransaction with calculation details
    """
    # Get applicable reward rate
    reward_rate = get_applicable_rate(transaction)

    # Calculate points
    if reward_rate.rate_type == 'points_per_dollar':
        points_earned = transaction.amount * Decimal(str(reward_rate.rate))
        formula = f"${transaction.amount} × {reward_rate.rate} points/dollar = {points_earned} points"
    elif reward_rate.rate_type == 'cashback_percent':
        points_earned = transaction.amount * (Decimal(str(reward_rate.rate)) / 100)
        formula = f"${transaction.amount} × {reward_rate.rate}% = ${points_earned} cashback"
    else:
        points_earned = Decimal('0')
        formula = "No rewards"

    # Create PointsTransaction
    points_txn = PointsTransaction(
        normalized_transaction_id=transaction.id,
        rewards_profile_id=reward_rate.profile_id,
        user_id=transaction.user_id,
        points_earned=points_earned,
        rate_applied=Decimal(str(reward_rate.rate)),
        category_used=transaction.category,
        rate_type=reward_rate.rate_type,
        calculation_formula=formula,
        status='earned',
        created_at=datetime.utcnow()
    )

    return points_txn
```

---

### Edge Case: Refunds

**Scenario**: You earned 300 points on a $100 purchase, then returned the item.

**Treatment**:
- Refund creates a new `NormalizedTransaction` with `type = 'refund'`
- Refund also earns rewards (negative points)

**Example**:
```
Purchase:
- Merchant: Best Buy
- Amount: $100.00
- Rate: 3% cashback
- Points Earned: $3.00

Refund:
- Merchant: Best Buy (refund)
- Amount: $100.00
- Rate: 3% cashback
- Points Earned: -$3.00 (negative)

Net Points: $3.00 - $3.00 = $0
```

**Implementation**:
```python
def calculate_rewards(transaction: NormalizedTransaction) -> PointsTransaction:
    # ... existing logic ...

    # Handle refunds (negative points)
    if transaction.transaction_type == 'refund':
        points_earned = -abs(points_earned)  # Make negative
        formula = f"Refund: -{formula}"

    return points_txn
```

---

## Time-Bound Promotions

### Problem: Rotating Reward Categories

**Example**: Discover It Card
- Q1 2026: 5% cashback on **groceries**
- Q2 2026: 5% cashback on **gas**
- Q3 2026: 5% cashback on **restaurants**
- Q4 2026: 5% cashback on **Amazon**

**Solution**: Multiple `RewardsProfile` records with date ranges

---

### Profile Structure

**Standard Profile** (Ongoing):
```json
{
  "id": "profile-discover-standard",
  "payment_instrument_id": "discover-1234",
  "profile_name": "Discover It - Standard",
  "valid_from": "2020-01-01",
  "valid_until": null,
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "other": 1.0
  },
  "is_promotion": false
}
```

**Q1 2026 Promotion**:
```json
{
  "id": "profile-discover-q1-2026",
  "payment_instrument_id": "discover-1234",
  "profile_name": "Discover It - Q1 2026 (Groceries 5%)",
  "valid_from": "2026-01-01",
  "valid_until": "2026-03-31",
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "groceries": 5.0,
    "other": 1.0
  },
  "is_promotion": true
}
```

**Q2 2026 Promotion**:
```json
{
  "id": "profile-discover-q2-2026",
  "payment_instrument_id": "discover-1234",
  "profile_name": "Discover It - Q2 2026 (Gas 5%)",
  "valid_from": "2026-04-01",
  "valid_until": "2026-06-30",
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "gas": 5.0,
    "other": 1.0
  },
  "is_promotion": true
}
```

---

### Profile Selection Logic

**Query**:
```sql
-- Get applicable rewards profile for transaction
SELECT *
FROM rewards_profiles
WHERE payment_instrument_id = :payment_instrument_id
  AND valid_from <= :transaction_date
  AND (valid_until IS NULL OR valid_until >= :transaction_date)
ORDER BY
  is_promotion DESC,  -- Promotions first
  valid_from DESC     -- Newest profile first
LIMIT 1;
```

**Example**:
```
Transaction: 2026-03-15 (groceries, $50)
Card: Discover It (1234)

Matching Profiles:
1. profile-discover-q1-2026 (Q1 2026 groceries 5%) ← Selected (is_promotion=true)
2. profile-discover-standard (standard 1%)

Selected: Q1 2026 promotion (5% groceries)
Points Earned: $50 × 5% = $2.50 cashback
```

---

## Manual Overrides

### Use Case: User Corrects Reward Rate

**Scenario**: Transaction categorized as "shopping" (1% back), but was actually at grocery store (5% back).

**Solution**: User manually overrides reward rate.

---

### PointsOverride Table

```sql
CREATE TABLE points_overrides (
    id UUID PRIMARY KEY,
    points_transaction_id UUID NOT NULL REFERENCES points_transactions(id),
    user_id UUID NOT NULL,

    -- Override Details
    original_rate NUMERIC(5, 2) NOT NULL,
    override_rate NUMERIC(5, 2) NOT NULL,
    original_category VARCHAR NOT NULL,
    override_category VARCHAR NOT NULL,

    -- Reason
    reason TEXT NOT NULL,  -- User explanation

    created_at TIMESTAMP NOT NULL
);
```

---

### Override Flow

**1. User Identifies Incorrect Categorization**:
```
Transaction: Amazon - $50.00
Category: shopping (auto-detected)
Rate: 1% = $0.50 cashback
```

**2. User Corrects Category**:
```
User Action: Change category to "groceries"
Reason: "This was Amazon Fresh (groceries), not general shopping"
```

**3. System Creates Override**:
```python
def create_override(
    points_transaction: PointsTransaction,
    new_category: str,
    reason: str,
    user: User
):
    # Get new rate for corrected category
    new_rate = get_rate_for_category(
        payment_instrument=points_transaction.payment_instrument,
        category=new_category,
        date=points_transaction.transaction_date
    )

    # Create override record
    override = PointsOverride(
        points_transaction_id=points_transaction.id,
        user_id=user.id,
        original_rate=points_transaction.rate_applied,
        override_rate=new_rate,
        original_category=points_transaction.category_used,
        override_category=new_category,
        reason=reason
    )
    db.add(override)

    # Update PointsTransaction
    points_transaction.rate_applied = new_rate
    points_transaction.category_used = new_category
    points_transaction.points_earned = calculate_points(
        amount=points_transaction.transaction.amount,
        rate=new_rate,
        rate_type=points_transaction.rate_type
    )
    points_transaction.calculation_formula = f"${points_transaction.transaction.amount} × {new_rate}% = ${points_transaction.points_earned} cashback (user override)"
    points_transaction.updated_at = datetime.utcnow()

    db.commit()
```

**4. Updated Points**:
```
Transaction: Amazon - $50.00
Category: groceries (user override)
Rate: 5% = $2.50 cashback
Override Reason: "This was Amazon Fresh (groceries), not general shopping"
```

---

## Points Lifecycle

### States

```
┌──────────┐
│ pending  │ ← Transaction not yet settled (authorization only)
└────┬─────┘
     │ Settlement confirmed
     ▼
┌──────────┐
│  earned  │ ← Points earned and available
└────┬─────┘
     │ User redeems points
     ▼
┌──────────┐
│ redeemed │ ← Points used for redemption
└────┬─────┘
     │ (Alternative: Points expire)
     ▼
┌──────────┐
│ expired  │ ← Points expired (e.g., after 2 years)
└──────────┘
```

---

### Aggregation Queries

**Total Earned Points**:
```sql
SELECT SUM(points_earned)
FROM points_transactions
WHERE user_id = :user_id
  AND payment_instrument_id = :card_id
  AND status = 'earned';
```

**Total Redeemed Points**:
```sql
SELECT SUM(points_redeemed)
FROM points_redemptions
WHERE user_id = :user_id
  AND payment_instrument_id = :card_id;
```

**Available Points**:
```sql
SELECT
  (SELECT SUM(points_earned) FROM points_transactions WHERE user_id = :user_id AND payment_instrument_id = :card_id AND status = 'earned') -
  (SELECT COALESCE(SUM(points_redeemed), 0) FROM points_redemptions WHERE user_id = :user_id AND payment_instrument_id = :card_id)
AS available_points;
```

---

## Reimbursement Handling

### Key Principle: Reimbursements Do NOT Claw Back Points

**Rationale**: You used the credit card, so you earned the rewards. The fact that someone reimbursed you is irrelevant to the issuer.

**Example**:
```
Scenario:
- You paid $100 for dinner on Chase Sapphire Reserve (3% dining)
- Earned: 300 points
- Friend reimbursed you $100 via Venmo

Result:
- You keep the 300 points
- Your net spend is $0 (fully reimbursed)
- Rewards are "free money" for you

Calculation:
- Purchase: $100 × 3% = 300 points (status: earned)
- Reimbursement: Does NOT affect PointsTransaction
- Available Points: 300 (unchanged)
```

---

### Implementation

**PointsTransaction is Independent of Reimbursements**:

```python
def calculate_rewards(transaction: NormalizedTransaction) -> PointsTransaction:
    """
    Calculate rewards based on transaction amount.
    Reimbursement status is IGNORED.
    """
    # Use ORIGINAL transaction amount (not net_amount)
    points_earned = transaction.amount * rate  # Not transaction.net_amount

    return PointsTransaction(
        points_earned=points_earned,
        # ... other fields ...
    )
```

**UI Display**:
```
┌──────────────────────────────────────────────────────────┐
│ Fancy Restaurant                                         │
│ Feb 8, 2026 • Chase Sapphire Reserve (••5678)           │
├──────────────────────────────────────────────────────────┤
│ Purchase Amount:        $100.00                          │
│ Reimbursements:         $75.00                           │
│   ✓ Sarah               $25.00                           │
│   ✓ Mike                $25.00                           │
│   ✓ Emily               $25.00                           │
│ ─────────────────────────────────                        │
│ Net Cost:               $25.00                           │
│                                                          │
│ 💎 Rewards Earned:      300 points (3% dining)          │
│    You keep these even though 75% was reimbursed!       │
└──────────────────────────────────────────────────────────┘
```

---

## Example Calculations

### Example 1: Simple Purchase (Chase Sapphire Reserve)

**Card Profile**:
```json
{
  "card": "Chase Sapphire Reserve",
  "default_rate": 1.0,
  "rate_type": "points_per_dollar",
  "category_rates": {
    "dining": 3.0,
    "travel": 3.0,
    "other": 1.0
  }
}
```

**Transaction**:
```
Merchant: Blue Bottle Coffee
Amount: $12.50
Category: dining (auto-detected)
Date: 2026-02-10
```

**Calculation**:
```
Rate: 3.0 points per dollar (dining category)
Points Earned: $12.50 × 3.0 = 37.5 points
Formula: "$12.50 × 3.0 points/dollar = 37.5 points"
```

**PointsTransaction Record**:
```json
{
  "id": "pts-001",
  "normalized_transaction_id": "txn-001",
  "rewards_profile_id": "profile-chase-sapphire",
  "points_earned": 37.5,
  "rate_applied": 3.0,
  "category_used": "dining",
  "rate_type": "points_per_dollar",
  "calculation_formula": "$12.50 × 3.0 points/dollar = 37.5 points",
  "status": "earned"
}
```

---

### Example 2: Discover It Rotating 5% (Q1 2026 Groceries)

**Standard Profile**:
```json
{
  "profile_name": "Discover It - Standard",
  "valid_from": "2020-01-01",
  "valid_until": null,
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "other": 1.0
  },
  "is_promotion": false
}
```

**Q1 2026 Promotion**:
```json
{
  "profile_name": "Discover It - Q1 2026 (Groceries 5%)",
  "valid_from": "2026-01-01",
  "valid_until": "2026-03-31",
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "groceries": 5.0,
    "other": 1.0
  },
  "is_promotion": true
}
```

**Transaction (Q1 2026)**:
```
Merchant: Whole Foods
Amount: $75.00
Category: groceries
Date: 2026-02-15 (within Q1 promotion)
```

**Calculation**:
```
Applicable Profile: Q1 2026 Promotion (is_promotion=true takes precedence)
Rate: 5.0% cashback (groceries during promotion)
Cashback Earned: $75.00 × 5% = $3.75
Formula: "$75.00 × 5% = $3.75 cashback (Q1 2026 groceries promotion)"
```

**Transaction (Q2 2026)**:
```
Merchant: Whole Foods
Amount: $75.00
Category: groceries
Date: 2026-04-15 (Q1 promotion ended)
```

**Calculation**:
```
Applicable Profile: Standard (Q1 promotion expired)
Rate: 1.0% cashback (standard rate)
Cashback Earned: $75.00 × 1% = $0.75
Formula: "$75.00 × 1% = $0.75 cashback"
```

---

### Example 3: Amex Blue Cash Preferred (Tiered Rates)

**Card Profile**:
```json
{
  "card": "Amex Blue Cash Preferred",
  "default_rate": 1.0,
  "rate_type": "cashback_percent",
  "category_rates": {
    "groceries": 6.0,   // Up to $6,000/year, then 1%
    "gas": 3.0,
    "transit": 3.0,
    "streaming": 6.0,
    "other": 1.0
  }
}
```

**Transaction**:
```
Merchant: Safeway
Amount: $120.00
Category: groceries
Date: 2026-02-10
```

**Calculation (Before $6k Cap)**:
```
Rate: 6.0% cashback (groceries)
Cashback Earned: $120.00 × 6% = $7.20
Formula: "$120.00 × 6% = $7.20 cashback (groceries)"
```

**Calculation (After $6k Cap)**:
```
Year-to-Date Groceries: $6,100 (exceeds $6,000 cap)
Rate: 1.0% cashback (cap reached)
Cashback Earned: $120.00 × 1% = $1.20
Formula: "$120.00 × 1% = $1.20 cashback (groceries cap reached)"
```

**Implementation Note**: Cap tracking requires additional logic (see V2).

---

### Example 4: Manual Override

**Original Transaction**:
```
Merchant: Amazon
Amount: $50.00
Category: shopping (auto-detected)
Rate: 1.0% = $0.50 cashback
```

**User Correction**:
```
User overrides category to "groceries"
Reason: "This was Amazon Fresh (groceries), not general shopping"
```

**Recalculation**:
```
Rate: 6.0% cashback (groceries for Amex Blue Cash Preferred)
Cashback Earned: $50.00 × 6% = $3.00
Formula: "$50.00 × 6% = $3.00 cashback (user override: groceries)"
Delta: +$2.50 ($3.00 - $0.50)
```

**PointsTransaction Update**:
```json
{
  "id": "pts-002",
  "points_earned": 3.00,  // Updated from 0.50
  "rate_applied": 6.0,    // Updated from 1.0
  "category_used": "groceries",  // Updated from shopping
  "calculation_formula": "$50.00 × 6% = $3.00 cashback (user override: groceries)"
}
```

---

### Example 5: Refund (Negative Points)

**Original Purchase**:
```
Merchant: Best Buy
Amount: $200.00
Category: shopping
Rate: 1.0% = $2.00 cashback
```

**Refund**:
```
Merchant: Best Buy (refund)
Amount: $200.00
Category: shopping
Rate: 1.0% = -$2.00 cashback (negative)
```

**Net Points**:
```
Purchase: +$2.00
Refund: -$2.00
────────────────
Net: $0.00
```

---

### Example 6: Reimbursed Purchase (Points Retained)

**Purchase**:
```
Merchant: Fancy Restaurant
Amount: $100.00
Category: dining
Rate: 3% = 300 points (Chase Sapphire Reserve)
```

**Reimbursement** (from friend):
```
Merchant: Venmo from Sarah
Amount: $100.00
Type: transfer
(No points transaction - this is not a credit card purchase)
```

**Result**:
```
Original Transaction:
- Gross: $100.00
- Reimbursed: $100.00
- Net: $0.00

Points:
- Earned: 300 points (unchanged by reimbursement)
- Available: 300 points
- You keep the points even though expense was fully reimbursed!
```

---

## Implementation Guide

### API Endpoints

**File: `backend/app/rewards/routes.py`**

```python
from fastapi import APIRouter, Depends
from app.db.session import get_db
from app.auth.middleware import get_current_user
from app.rewards.calculator import calculate_rewards

router = APIRouter(prefix="/rewards", tags=["rewards"])

# ============================================================================
# Get Rewards Summary for User
# ============================================================================

@router.get("/summary")
def get_rewards_summary(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Get rewards summary across all cards."""
    cards = db.query(PaymentInstrument).filter(
        PaymentInstrument.user_id == current_user.id,
        PaymentInstrument.type == 'credit_card'
    ).all()

    summary = []
    for card in cards:
        # Total earned
        earned = db.query(func.sum(PointsTransaction.points_earned)).filter(
            PointsTransaction.user_id == current_user.id,
            PointsTransaction.payment_instrument_id == card.id,
            PointsTransaction.status == 'earned'
        ).scalar() or 0

        # Total redeemed
        redeemed = db.query(func.sum(PointsRedemption.points_redeemed)).filter(
            PointsRedemption.user_id == current_user.id,
            PointsRedemption.payment_instrument_id == card.id
        ).scalar() or 0

        summary.append({
            "card": card.display_name,
            "earned": float(earned),
            "redeemed": float(redeemed),
            "available": float(earned - redeemed)
        })

    return {"cards": summary}


# ============================================================================
# Recalculate Rewards (After Category Override)
# ============================================================================

@router.post("/transactions/{transaction_id}/recalculate")
def recalculate_rewards(
    transaction_id: str,
    override_data: dict,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Recalculate rewards after user overrides category."""
    transaction = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id,
        NormalizedTransaction.user_id == current_user.id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update category
    old_category = transaction.category
    transaction.category = override_data['new_category']

    # Recalculate rewards
    points_txn = db.query(PointsTransaction).filter(
        PointsTransaction.normalized_transaction_id == transaction.id
    ).first()

    if points_txn:
        # Create override record
        override = PointsOverride(
            points_transaction_id=points_txn.id,
            user_id=current_user.id,
            original_rate=points_txn.rate_applied,
            original_category=old_category,
            override_category=transaction.category,
            reason=override_data.get('reason', 'User override')
        )

        # Recalculate
        new_points_txn = calculate_rewards(transaction)
        points_txn.points_earned = new_points_txn.points_earned
        points_txn.rate_applied = new_points_txn.rate_applied
        points_txn.category_used = new_points_txn.category_used
        points_txn.calculation_formula = new_points_txn.calculation_formula
        points_txn.updated_at = datetime.utcnow()

        db.add(override)
        db.commit()

    return {"message": "Rewards recalculated", "new_points": float(points_txn.points_earned)}
```

---

### Background Job: Calculate Rewards for New Transactions

**File: `backend/app/jobs/rewards_calculator.py`**

```python
from celery import Celery
from app.rewards.calculator import calculate_rewards

app = Celery('spendi', broker='redis://localhost:6379/0')

@app.task
def calculate_rewards_for_transaction(transaction_id: str):
    """Calculate rewards for newly normalized transaction."""
    db = next(get_db())

    transaction = db.query(NormalizedTransaction).filter(
        NormalizedTransaction.id == transaction_id
    ).first()

    if not transaction:
        return

    # Only calculate rewards for credit card purchases
    payment_instrument = transaction.payment_instrument
    if payment_instrument.type != 'credit_card':
        return

    # Check if already calculated
    existing = db.query(PointsTransaction).filter(
        PointsTransaction.normalized_transaction_id == transaction.id
    ).first()

    if existing:
        return  # Already calculated

    # Calculate rewards
    points_txn = calculate_rewards(transaction)
    db.add(points_txn)
    db.commit()

    logger.info(f"Calculated rewards for transaction {transaction_id}: {points_txn.points_earned} points")
```

**Trigger**: Called after `NormalizedTransaction` is created.

---

### Testing Strategy

```python
import pytest
from decimal import Decimal

def test_rewards_calculation_points_per_dollar(db_session):
    """Test rewards calculation with points per dollar."""
    # Setup: Create card with rewards profile
    card = create_credit_card(name="Chase Sapphire Reserve", last_four="5678")
    profile = RewardsProfile(
        payment_instrument_id=card.id,
        default_rate=Decimal('1.0'),
        rate_type='points_per_dollar',
        category_rates={'dining': Decimal('3.0')}
    )
    db_session.add(profile)

    # Create transaction
    transaction = NormalizedTransaction(
        user_id=user.id,
        payment_instrument_id=card.id,
        amount=Decimal('12.50'),
        category='dining'
    )
    db_session.add(transaction)
    db_session.commit()

    # Calculate rewards
    points_txn = calculate_rewards(transaction)

    # Assertions
    assert points_txn.points_earned == Decimal('37.5')  # 12.50 × 3.0
    assert points_txn.rate_applied == Decimal('3.0')
    assert points_txn.category_used == 'dining'


def test_time_bound_promotion(db_session):
    """Test that promotion rate takes precedence over standard rate."""
    card = create_credit_card()

    # Standard profile (1% all categories)
    standard = RewardsProfile(
        payment_instrument_id=card.id,
        valid_from=date(2020, 1, 1),
        valid_until=None,
        default_rate=Decimal('1.0'),
        rate_type='cashback_percent',
        category_rates={'other': Decimal('1.0')},
        is_promotion=False
    )

    # Q1 2026 promotion (5% groceries)
    promotion = RewardsProfile(
        payment_instrument_id=card.id,
        valid_from=date(2026, 1, 1),
        valid_until=date(2026, 3, 31),
        default_rate=Decimal('1.0'),
        rate_type='cashback_percent',
        category_rates={'groceries': Decimal('5.0')},
        is_promotion=True
    )
    db_session.add_all([standard, promotion])

    # Transaction during promotion
    transaction = NormalizedTransaction(
        payment_instrument_id=card.id,
        amount=Decimal('50.00'),
        category='groceries',
        transaction_date=date(2026, 2, 15)  # Q1 2026
    )
    db_session.commit()

    # Calculate rewards
    points_txn = calculate_rewards(transaction)

    # Should use promotion rate (5%), not standard (1%)
    assert points_txn.points_earned == Decimal('2.50')  # 50.00 × 5%
    assert points_txn.rate_applied == Decimal('5.0')
```

---

## Document History

| Version | Date       | Author      | Changes                        |
|---------|------------|-------------|--------------------------------|
| 1.0     | 2026-02-11 | Engineering | Initial rewards engine design  |

---

**Questions? Contact**: engineering@spendi.app