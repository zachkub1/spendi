# UI/UX Design: Spendi
**Version**: 1.0
**Last Updated**: 2026-02-11
**Status**: Draft
**Owner**: Product & Design

---

## Overview

Spendi's UI is designed around three core principles:

1. **Financial Clarity > Aesthetics**: Users should instantly understand where their money went and why
2. **Explainability**: Every number, calculation, and insight is traceable back to source data
3. **Trust Through Transparency**: No dark patterns, no hidden costs, no data games

**Design Language**: Clean, minimal, data-dense (inspired by spreadsheets and financial dashboards)

**Tech Stack**: Next.js 14 (App Router), Tailwind CSS, shadcn/ui components, React Server Components

---

## Table of Contents

1. [Design Principles](#design-principles)
2. [Information Architecture](#information-architecture)
3. [Page Designs](#page-designs)
4. [Component Library](#component-library)
5. [State Management](#state-management)
6. [Responsive Design](#responsive-design)
7. [Accessibility](#accessibility)
8. [Dark Mode](#dark-mode)

---

## Design Principles

### 1. Financial Clarity First

**Good**: Large numbers, clear labels, obvious hierarchy
```
February Spending
─────────────────────────
$2,450.00  Gross
-$  450.00  Reimbursed
═════════════════════════
$2,000.00  Net Personal
```

**Bad**: Small text, vague labels, unclear relationships
```
Spending: $2,450 (some reimbursed)
Net: $2,000
```

---

### 2. Inline Explainability

**Every calculated number has a "?" icon that shows the formula**

Example:
```
Net Spending: $2,000.00 [?]

Hover tooltip:
┌─────────────────────────────────┐
│ Net Spending Calculation        │
├─────────────────────────────────┤
│ Gross Spending:     $2,450.00   │
│ - Reimbursements:   $  450.00   │
│ ─────────────────────────────   │
│ = Net Personal:     $2,000.00   │
│                                 │
│ View 12 reimbursed transactions │
└─────────────────────────────────┘
```

---

### 3. No Dark Patterns

**What We DON'T Do**:
- ❌ Hide costs or fees
- ❌ Make it hard to delete account
- ❌ Pre-select opt-ins for marketing
- ❌ Use confusing language to trick users
- ❌ Make privacy settings hard to find

**What We DO**:
- ✅ Prominent "Delete Account" button in Settings
- ✅ Clear explanation of what data we collect
- ✅ One-click export of all data
- ✅ Plain English (no financial jargon)

---

### 4. Mobile-First

**Breakpoints**:
- Mobile: 320px - 767px (single column, stacked cards)
- Tablet: 768px - 1023px (two columns where appropriate)
- Desktop: 1024px+ (three columns, expanded detail panels)

**Touch Targets**: Minimum 44×44px (WCAG 2.1 guideline)

---

## Information Architecture

### Site Map

```
┌─────────────────────────────────────────────────────────┐
│ Spendi                                                │
└─────────────────────────────────────────────────────────┘
           │
           ├── Dashboard (/)
           │   ├── Net Spending Summary
           │   ├── Recent Transactions (last 10)
           │   ├── Pending Reimbursements
           │   └── Rewards Summary
           │
           ├── Transactions (/transactions)
           │   ├── List View (all transactions)
           │   ├── Filters (date, card, category, status)
           │   ├── Search (merchant, amount)
           │   └── Detail View (/transactions/:id)
           │       ├── Transaction Info
           │       ├── Reimbursements (side-by-side)
           │       ├── Rewards Earned
           │       └── Edit/Link Actions
           │
           ├── Cards & Rewards (/cards)
           │   ├── Card List (all payment instruments)
           │   ├── Card Detail (/cards/:id)
           │   │   ├── Reward Rules
           │   │   ├── Points Summary
           │   │   └── Transaction History (this card only)
           │   └── Add New Card
           │
           ├── Email Connections (/email)
           │   ├── Connected Accounts
           │   ├── Sync Status
           │   ├── Connect New Account
           │   └── Revoke Access
           │
           └── Settings (/settings)
               ├── Profile
               ├── Privacy & Data
               ├── Export Data
               └── Delete Account
```

---

## Page Designs

### Page 1: Dashboard

**Purpose**: At-a-glance financial summary for current month

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [☰] Spendi                    [👤] John  [Feb 2026 ▼]   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ February 2026 Summary                                  ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │  Gross Spending              $2,450.00                ││
│ │  Total Reimbursed            -$  450.00               ││
│ │  ────────────────────────────────────                 ││
│ │  Net Personal Spending       $2,000.00  [?]           ││
│ │                                                        ││
│ │  By Category (Net):                                   ││
│ │  • Dining          $500  ━━━━━━━━━━ 25%              ││
│ │  • Groceries       $400  ━━━━━━━━ 20%                ││
│ │  • Transportation  $300  ━━━━━━ 15%                  ││
│ │  • Entertainment   $250  ━━━━━ 12.5%                 ││
│ │  • Other           $550  ━━━━━━━━━━━ 27.5%           ││
│ │                                                        ││
│ │  [View All Transactions]                               ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌──────────────────────────┐ ┌───────────────────────────┐│
│ │ Pending Reimbursements   │ │ Rewards Earned            ││
│ ├──────────────────────────┤ ├───────────────────────────┤│
│ │                          │ │                           ││
│ │ ⏳ Concert Tickets       │ │ 💎 5,240 points           ││
│ │    $50 from Sarah        │ │    Chase Sapphire Reserve ││
│ │    Expected: Feb 20      │ │                           ││
│ │                          │ │ 💵 $42.50 cashback        ││
│ │ ⏳ Work Lunch            │ │    Discover It            ││
│ │    $30 from employer     │ │                           ││
│ │    Expected: Feb 28      │ │ [View All Cards]          ││
│ │                          │ │                           ││
│ │ Total Expected: $80.00   │ │                           ││
│ └──────────────────────────┘ └───────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Recent Transactions                                    ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Feb 10  Venmo from Sarah       +$50.00                ││
│ │         [Linked to Blue Bottle]                       ││
│ │                                                        ││
│ │ Feb 9   🟢 Blue Bottle Coffee   $50.00   Net: $0     ││
│ │         Reimbursed by Sarah                           ││
│ │                                                        ││
│ │ Feb 8   🟡 Fancy Restaurant    $100.00   Net: $25    ││
│ │         Partially reimbursed (75%)                    ││
│ │                                                        ││
│ │ Feb 7   🔴 Grocery Store        $75.00               ││
│ │                                                        ││
│ │ Feb 6   ⏳ Concert Tickets     $100.00   Net: $100   ││
│ │         Expecting $50 from Sarah                      ││
│ │                                                        ││
│ │ [View All →]                                           ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<MonthSelector>` - Dropdown to change month
- `<SpendingSummaryCard>` - Gross/Reimbursed/Net with tooltip explainer
- `<CategoryBreakdown>` - Horizontal bar chart with percentages
- `<PendingReimbursementsCard>` - List of expected reimbursements
- `<RewardsSummaryCard>` - Total points/cashback earned
- `<RecentTransactionsList>` - Last 10 transactions with status indicators

**Interactions**:
- Click category bar → filter transactions by that category
- Click pending reimbursement → go to transaction detail
- Click reward card name → go to card detail
- Click recent transaction → go to transaction detail

---

### Page 2: Transactions Ledger

**Purpose**: Full list of all transactions with filtering and search

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [←] Transactions                                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌──────────────────────────────────────────────────────┐  │
│ │ [🔍 Search transactions...                          ]│  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ Filters: [All Cards ▼] [All Categories ▼] [All Time ▼]   │
│          [✓ Purchases] [✓ Reimbursements] [✓ Refunds]    │
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ 127 transactions • Net: $2,000.00                      ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ ┌────────────────────────────────────────────────────┐││
│ │ │ Feb 10 • Chase Sapphire (••5678)                   │││
│ │ ├────────────────────────────────────────────────────┤││
│ │ │ Venmo from Sarah                     +$50.00       │││
│ │ │ [Linked to Blue Bottle Coffee]       transfer      │││
│ │ └────────────────────────────────────────────────────┘││
│ │                                                        ││
│ │ ┌────────────────────────────────────────────────────┐││
│ │ │ Feb 9 • Chase Sapphire (••5678)                    │││
│ │ ├────────────────────────────────────────────────────┤││
│ │ │ 🟢 Blue Bottle Coffee                $50.00        │││
│ │ │ Dining                               Net: $0.00    │││
│ │ │ Reimbursed: $50.00 by Sarah                        │││
│ │ │ Rewards: 150 points (3×)                           │││
│ │ └────────────────────────────────────────────────────┘││
│ │                                                        ││
│ │ ┌────────────────────────────────────────────────────┐││
│ │ │ Feb 8 • Chase Sapphire (••5678)                    │││
│ │ ├────────────────────────────────────────────────────┤││
│ │ │ 🟡 Fancy Restaurant                 $100.00        │││
│ │ │ Dining                              Net: $25.00    │││
│ │ │ Reimbursed: $75.00 (3 payments)                    │││
│ │ │ Rewards: 300 points (3×)                           │││
│ │ └────────────────────────────────────────────────────┘││
│ │                                                        ││
│ │ [Load More]                                            ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<SearchBar>` - Full-text search (merchant, amount, notes)
- `<FilterBar>` - Card, category, date range, transaction type filters
- `<TransactionCard>` - Expandable card with summary
- `<ReimbursementStatusBadge>` - 🟢 Full, 🟡 Partial, ⏳ Expected, 🔴 None

**Interactions**:
- Click transaction card → go to detail view
- Click filter → update list
- Search → debounced query (300ms)
- Scroll → infinite scroll (load 50 at a time)

---

### Page 3: Transaction Detail View

**Purpose**: Detailed view of a single transaction with reimbursements side-by-side

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [←] Blue Bottle Coffee                                     │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Transaction Details                                    ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Blue Bottle Coffee                                     ││
│ │ February 9, 2026 at 2:15 PM                            ││
│ │                                                        ││
│ │ Chase Sapphire Reserve (••5678)                        ││
│ │ Category: Dining (95% confident) [Edit]                ││
│ │                                                        ││
│ │ ──────────────────────────────────────                 ││
│ │ Purchase Amount                      $50.00            ││
│ │ ──────────────────────────────────────                 ││
│ │                                                        ││
│ │ Reimbursements                                         ││
│ │ ✓ Venmo from Sarah      $50.00   Feb 10               ││
│ │ ──────────────────────────────────────                 ││
│ │ Total Reimbursed                     $50.00            ││
│ │                                                        ││
│ │ ══════════════════════════════════════                 ││
│ │ Net Personal Cost                    $0.00  [?]        ││
│ │ ══════════════════════════════════════                 ││
│ │                                                        ││
│ │ [+ Link Reimbursement] [+ Add Expected]                ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Rewards Earned                                         ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ 💎 150 points                                          ││
│ │                                                        ││
│ │ $50.00 × 3.0 points/dollar = 150 points               ││
│ │ (3× dining category)                                   ││
│ │                                                        ││
│ │ You keep these even though the expense was            ││
│ │ fully reimbursed!                                      ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Notes                                                  ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Coffee with Sarah, discussed project planning.         ││
│ │                                                        ││
│ │ [Edit]                                                 ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Audit Trail                                            ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Feb 10, 2:30 PM  Reimbursement linked (system)        ││
│ │ Feb 9, 2:20 PM   Transaction created (email)          ││
│ │ Feb 9, 2:15 PM   Transaction occurred                 ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ [Delete Transaction]                                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Side-by-Side Reimbursement Example** (Multiple Reimbursements):
```
┌────────────────────────────────────────────────────────────┐
│ Fancy Restaurant                                           │
│ February 8, 2026 at 7:30 PM                                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌─────────────────────┐  ┌────────────────────────────┐   │
│ │ Original Purchase   │  │ Reimbursements             │   │
│ ├─────────────────────┤  ├────────────────────────────┤   │
│ │                     │  │                            │   │
│ │ Amount: $100.00     │  │ ✓ Venmo from Sarah         │   │
│ │ Card: Chase (5678)  │  │   $25.00  •  Feb 9         │   │
│ │ Category: Dining    │  │                            │   │
│ │ Date: Feb 8         │  │ ✓ Zelle from Mike          │   │
│ │                     │  │   $25.00  •  Feb 10        │   │
│ │ Rewards:            │  │                            │   │
│ │ 300 points (3×)     │  │ ✓ Cash App from Emily      │   │
│ │                     │  │   $25.00  •  Feb 11        │   │
│ │                     │  │                            │   │
│ │                     │  │ ────────────────────────   │   │
│ │                     │  │ Total: $75.00              │   │
│ │                     │  │                            │   │
│ └─────────────────────┘  └────────────────────────────┘   │
│                                                            │
│ ══════════════════════════════════════════════════════════ │
│ Net Personal Cost: $25.00                                  │
│ (Your share: 25% of total)                                 │
│ ══════════════════════════════════════════════════════════ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<TransactionHeader>` - Merchant, date, card
- `<AmountBreakdown>` - Purchase → Reimbursements → Net (with formula tooltip)
- `<ReimbursementList>` - List of linked reimbursements with dates
- `<RewardsCard>` - Points earned with calculation explanation
- `<NotesEditor>` - User notes (editable)
- `<AuditTrail>` - Chronological log of changes

**Interactions**:
- Click "Link Reimbursement" → modal to select unlinked transfer
- Click "Add Expected" → modal to add expected reimbursement (not yet received)
- Click "Edit" category → dropdown to change category (triggers rewards recalculation)
- Click [?] tooltip → show net cost calculation formula

---

### Page 4: Cards & Rewards

**Purpose**: Manage payment instruments and view rewards summary

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [←] Cards & Rewards                                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Chase Sapphire Reserve                                 ││
│ │ ••5678 • Active                                         ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ 💎 Rewards Earned                                      ││
│ │ ────────────────────────────────────────               ││
│ │ This Month:        5,240 points                        ││
│ │ All Time:          67,830 points                       ││
│ │ Available:         67,830 points (none redeemed)       ││
│ │                                                        ││
│ │ 📊 Reward Structure                                    ││
│ │ ────────────────────────────────────                   ││
│ │ • Dining:          3× points                           ││
│ │ • Travel:          3× points                           ││
│ │ • Other:           1× point                            ││
│ │ Annual Fee:        $550                                ││
│ │                                                        ││
│ │ [View Transactions] [Edit Rewards]                     ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Discover It                                            ││
│ │ ••1234 • Active                                         ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ 💵 Cashback Earned                                     ││
│ │ ────────────────────────────────────                   ││
│ │ This Month:        $42.50                              ││
│ │ All Time:          $1,285.00                           ││
│ │ Available:         $1,285.00                           ││
│ │                                                        ││
│ │ 📊 Reward Structure (Q1 2026)                          ││
│ │ ────────────────────────────────────                   ││
│ │ • Groceries:       5% (until Mar 31) 🔥               ││
│ │ • Other:           1%                                  ││
│ │ Annual Fee:        $0                                  ││
│ │                                                        ││
│ │ 💡 Tip: Q2 2026 will be 5% on gas                     ││
│ │                                                        ││
│ │ [View Transactions] [Edit Rewards]                     ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Venmo (@johndoe)                                       ││
│ │ P2P Account • Active                                    ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ No rewards for P2P transfers                           ││
│ │                                                        ││
│ │ [View Transactions] [Disconnect]                       ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ [+ Add New Card]                                           │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Card Detail View** (Click "View Transactions"):
```
┌────────────────────────────────────────────────────────────┐
│ [←] Chase Sapphire Reserve (••5678)                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Rewards Summary                                        ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ February 2026:     5,240 points                        ││
│ │ All Time:          67,830 points                       ││
│ │                                                        ││
│ │ By Category (This Month):                              ││
│ │ • Dining:          3,600 pts  (1,200 spent @ 3×)      ││
│ │ • Travel:          1,200 pts  (400 spent @ 3×)        ││
│ │ • Other:           440 pts    (440 spent @ 1×)        ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Transactions (This Card Only)                          ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Feb 10  Blue Bottle Coffee    $50.00   150 pts        ││
│ │ Feb 8   Fancy Restaurant     $100.00   300 pts        ││
│ │ Feb 7   Grocery Store         $75.00    75 pts        ││
│ │ ...                                                    ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Rewards Optimization                                   ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ 💡 You could earn more rewards:                        ││
│ │                                                        ││
│ │ • You spent $300 on groceries using this card (1×)     ││
│ │   Discover It offers 5% on groceries (Q1 2026)        ││
│ │   Potential gain: $15 vs 300 points (~$4.50 value)    ││
│ │                                                        ││
│ │ [View All Optimization Tips]                           ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<CardSummaryCard>` - Card name, last 4, rewards summary
- `<RewardStructureList>` - Reward rates by category
- `<PromotionBadge>` - Highlight time-bound promotions (🔥)
- `<OptimizationTips>` - Suggestions for better card usage

---

### Page 5: Email Connections

**Purpose**: Manage Gmail API connections for transaction ingestion

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [←] Email Connections                                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ How Email Sync Works                                   ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Spendi reads transaction emails from your inbox to   ││
│ │ automatically track purchases and reimbursements.      ││
│ │                                                        ││
│ │ ✅ What we do:                                         ││
│ │ • Read emails from banks and payment apps              ││
│ │ • Extract merchant, amount, and date                   ││
│ │ • Delete email content (keep transaction data only)    ││
│ │                                                        ││
│ │ ❌ What we DON'T do:                                   ││
│ │ • Read personal emails                                 ││
│ │ • Store full email content                             ││
│ │ • Send emails or modify your inbox                     ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ ✅ john.doe@gmail.com                                  ││
│ │ Connected • Last synced: 2 hours ago                   ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Sync Status:       ✓ Active                            ││
│ │ Transactions:      127 synced this month               ││
│ │ Last Sync:         Feb 11, 2026 at 10:00 AM           ││
│ │ Next Sync:         Feb 12, 2026 at 2:00 AM            ││
│ │                                                        ││
│ │ [Sync Now] [Pause Sync] [Disconnect]                   ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Supported Email Providers                              ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ We automatically detect transactions from:             ││
│ │                                                        ││
│ │ Credit Cards:                                          ││
│ │ • Chase, American Express, Citi, Discover,             ││
│ │   Capital One, Bank of America                         ││
│ │                                                        ││
│ │ P2P Payment Apps:                                      ││
│ │ • Venmo, Zelle, Cash App, PayPal                       ││
│ │                                                        ││
│ │ Don't see your bank? [Request Support]                 ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ [+ Connect Another Email Account]                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<EmailAccountCard>` - Connected account with sync status
- `<SyncStatusIndicator>` - Visual indicator (✓ Active, ⏸ Paused, ❌ Error)
- `<SupportedProvidersGrid>` - List of supported banks/apps

**Interactions**:
- Click "Sync Now" → trigger immediate sync (show loading spinner)
- Click "Pause Sync" → disable auto-sync (confirm modal)
- Click "Disconnect" → revoke OAuth access (confirm with re-auth modal)
- Click "Connect Another Email Account" → OAuth flow

---

### Page 6: Settings & Privacy

**Purpose**: User profile, privacy controls, data export, account deletion

**Layout**:
```
┌────────────────────────────────────────────────────────────┐
│ [←] Settings                                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Profile                                                ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Name:          John Doe                                ││
│ │ Email:         john.doe@gmail.com                      ││
│ │ Timezone:      America/Los_Angeles                     ││
│ │                                                        ││
│ │ [Edit Profile]                                         ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Privacy & Data                                         ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ What data we collect:                                  ││
│ │ • Transaction details from emails                      ││
│ │ • Payment instrument names and last 4 digits           ││
│ │ • Your reward preferences and manual overrides         ││
│ │                                                        ││
│ │ What we DON'T collect:                                 ││
│ │ • Full email content (deleted after extraction)        ││
│ │ • Bank account credentials                             ││
│ │ • Full credit card numbers                             ││
│ │                                                        ││
│ │ [Read Full Privacy Policy]                             ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ Data Export                                            ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Export all your data in JSON or CSV format.            ││
│ │                                                        ││
│ │ Includes:                                              ││
│ │ • All transactions                                     ││
│ │ • Payment instruments                                  ││
│ │ • Reimbursement links                                  ││
│ │ • Rewards history                                      ││
│ │ • Audit logs                                           ││
│ │                                                        ││
│ │ [Export as JSON] [Export as CSV]                       ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
│ ┌────────────────────────────────────────────────────────┐│
│ │ ⚠️ Danger Zone                                         ││
│ ├────────────────────────────────────────────────────────┤│
│ │                                                        ││
│ │ Delete Account                                         ││
│ │                                                        ││
│ │ This will:                                             ││
│ │ • Delete all your transactions                         ││
│ │ • Revoke email access                                  ││
│ │ • Remove all payment instruments                       ││
│ │ • Cancel any scheduled jobs                            ││
│ │                                                        ││
│ │ Your data will be deleted in 30 days. You can          ││
│ │ cancel deletion within that time.                      ││
│ │                                                        ││
│ │ [Delete My Account]                                    ││
│ │                                                        ││
│ └────────────────────────────────────────────────────────┘│
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Components**:
- `<ProfileCard>` - User info (name, email, timezone)
- `<PrivacyExplainer>` - Plain English explanation of data collection
- `<DataExportCard>` - One-click export buttons
- `<DangerZone>` - Account deletion with clear warning

**Interactions**:
- Click "Delete My Account" → modal with re-authentication → confirmation → soft delete
- Click "Export as JSON" → generate JSON file → download
- Click "Export as CSV" → generate CSV file → download

---

## Component Library

### Core Components (shadcn/ui based)

**Layout Components**:
- `<AppShell>` - Main app layout (nav, content area, footer)
- `<NavBar>` - Top navigation (logo, user menu, month selector)
- `<Sidebar>` - Desktop sidebar navigation (Dashboard, Transactions, Cards, Email, Settings)
- `<MobileNav>` - Mobile bottom tab bar

**Data Display Components**:
- `<Card>` - Generic card container
- `<Stat>` - Large number with label and optional tooltip
- `<Badge>` - Status indicator (Full, Partial, Expected, None)
- `<ProgressBar>` - Horizontal bar for category spending
- `<Tooltip>` - Hover explanation (calculation formulas)
- `<EmptyState>` - Placeholder when no data (e.g., "No transactions yet")

**Transaction Components**:
- `<TransactionCard>` - Summary card with merchant, amount, status
- `<TransactionList>` - List of transaction cards
- `<ReimbursementBadge>` - Visual indicator (🟢🟡⏳🔴)
- `<AmountDisplay>` - Formatted currency (e.g., "$1,234.56")
- `<CategoryTag>` - Category label with icon

**Form Components**:
- `<SearchBar>` - Debounced search input
- `<FilterDropdown>` - Multi-select filter (cards, categories, dates)
- `<DateRangePicker>` - Date range selector
- `<MonthSelector>` - Month/year dropdown

**Modal Components**:
- `<LinkReimbursementModal>` - Select unlinked transfer to link
- `<AddExpectedReimbursementModal>` - Form to add expected reimbursement
- `<ConfirmDeleteModal>` - Confirmation before delete
- `<ReAuthModal>` - Re-authenticate before sensitive action

**Explainer Components**:
- `<ExplainerTooltip>` - [?] icon with hover formula
- `<CalculationBreakdown>` - Step-by-step calculation display
- `<AuditTrail>` - Chronological log of changes

---

## State Management

### Approach: React Server Components + Client State

**Architecture**:
```
┌─────────────────────────────────────────────────────────────┐
│ Server Components (Next.js App Router)                     │
│ - Fetch data from API (server-side)                        │
│ - Render initial HTML with data                            │
│ - No client-side JavaScript for static content             │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Client Components (React State)                            │
│ - Interactive elements (filters, modals, forms)            │
│ - Local state for UI (open/closed, loading, errors)        │
│ - Optimistic updates (update UI immediately, sync later)   │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ API Routes (Next.js API)                                   │
│ - CRUD operations on transactions                          │
│ - Reimbursement linking                                    │
│ - Rewards recalculation                                    │
└─────────────────────────────────────────────────────────────┘
```

---

### State Categories

**1. Server State (Cached, Fetched on Load)**
- User profile
- Transactions list
- Cards & rewards profiles
- Email sync status

**2. Client State (Local, Ephemeral)**
- UI state (modal open/closed, loading spinners, toast notifications)
- Form state (input values, validation errors)
- Filter state (selected categories, date range)
- Search query (debounced)

**3. URL State (Shared, Bookmarkable)**
- Current month (e.g., `/dashboard?month=2026-02`)
- Transaction filters (e.g., `/transactions?category=dining&card=chase-5678`)
- Pagination offset (e.g., `/transactions?page=2`)

---

### Data Fetching Strategy

**Server Components** (Pages):
```tsx
// app/dashboard/page.tsx
export default async function DashboardPage() {
  // Fetch on server
  const summary = await getSummary();
  const recentTransactions = await getRecentTransactions();
  const rewards = await getRewardsSummary();

  return (
    <div>
      <SpendingSummaryCard data={summary} />
      <RecentTransactionsList data={recentTransactions} />
      <RewardsSummaryCard data={rewards} />
    </div>
  );
}
```

**Client Components** (Interactive):
```tsx
'use client';

export function LinkReimbursementButton({ transactionId }) {
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleLink = async (reimbursementId) => {
    // Optimistic update
    setIsModalOpen(false);

    // API call
    await linkReimbursement(transactionId, reimbursementId);

    // Revalidate server data
    router.refresh();
  };

  return (
    <>
      <Button onClick={() => setIsModalOpen(true)}>Link Reimbursement</Button>
      {isModalOpen && (
        <LinkReimbursementModal
          transactionId={transactionId}
          onLink={handleLink}
          onClose={() => setIsModalOpen(false)}
        />
      )}
    </>
  );
}
```

---

### Cache & Revalidation

**Next.js Cache Strategy**:
```tsx
// app/dashboard/page.tsx
export const revalidate = 3600; // Revalidate every 1 hour

// app/transactions/page.tsx
export const revalidate = 0; // Always fetch fresh data
```

**Manual Revalidation** (After Mutation):
```tsx
import { revalidatePath } from 'next/cache';

// After linking reimbursement
revalidatePath('/transactions');
revalidatePath('/dashboard');
```

---

## Responsive Design

### Breakpoints

**Mobile** (320px - 767px):
- Single column layout
- Bottom tab bar navigation
- Stacked cards
- Simplified tables (hide non-essential columns)

**Tablet** (768px - 1023px):
- Two-column layout where appropriate
- Sidebar navigation (collapsible)
- Card grid (2 columns)

**Desktop** (1024px+):
- Three-column layout for dashboards
- Expanded detail panels (side-by-side view)
- Full data tables

---

### Mobile-Specific Optimizations

**Transaction List (Mobile)**:
```
┌──────────────────────────────────┐
│ Feb 10                           │
│ Venmo from Sarah       +$50.00   │
│ [Linked to Blue Bottle]          │
├──────────────────────────────────┤
│ Feb 9                            │
│ 🟢 Blue Bottle Coffee             │
│ $50.00 • Net: $0.00              │
│ Reimbursed by Sarah              │
├──────────────────────────────────┤
│ Feb 8                            │
│ 🟡 Fancy Restaurant               │
│ $100.00 • Net: $25.00            │
│ 3 reimbursements                 │
└──────────────────────────────────┘
```

**Transaction Detail (Mobile)**:
```
┌──────────────────────────────────┐
│ [←] Blue Bottle Coffee           │
├──────────────────────────────────┤
│ Feb 9, 2026                      │
│ Chase Sapphire (••5678)          │
│                                  │
│ Purchase:      $50.00            │
│ Reimbursed:    $50.00            │
│ ─────────────────────            │
│ Net:           $0.00             │
│                                  │
│ Rewards:       150 pts           │
│                                  │
│ [Link] [Expected] [Edit]         │
└──────────────────────────────────┘
```

---

## Accessibility

### WCAG 2.1 Level AA Compliance

**1. Color Contrast**
- Text: 4.5:1 ratio minimum
- Large text (18pt+): 3:1 ratio
- Interactive elements: 3:1 ratio

**2. Keyboard Navigation**
- All interactive elements accessible via Tab
- Focus indicators visible (2px outline)
- Skip to main content link

**3. Screen Reader Support**
- Semantic HTML (`<nav>`, `<main>`, `<article>`)
- ARIA labels for icons
- Live regions for dynamic updates (e.g., "Transaction linked successfully")

**4. Touch Targets**
- Minimum 44×44px (iOS/Android guideline)
- Adequate spacing between buttons (8px minimum)

---

### Example: Accessible Transaction Card

```tsx
<article
  role="article"
  aria-labelledby={`transaction-${id}`}
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => e.key === 'Enter' && handleClick()}
>
  <h3 id={`transaction-${id}`}>
    {merchant} - {formatCurrency(amount)}
  </h3>
  <p>
    {reimbursementStatus === 'full' && (
      <span aria-label="Fully reimbursed">🟢</span>
    )}
    {category} • {formatDate(date)}
  </p>
</article>
```

---

## Dark Mode

### Color Palette

**Light Mode**:
- Background: `#FFFFFF`
- Surface: `#F9FAFB`
- Border: `#E5E7EB`
- Text Primary: `#111827`
- Text Secondary: `#6B7280`
- Accent (Blue): `#3B82F6`
- Success (Green): `#10B981`
- Warning (Yellow): `#F59E0B`
- Danger (Red): `#EF4444`

**Dark Mode**:
- Background: `#0F172A`
- Surface: `#1E293B`
- Border: `#334155`
- Text Primary: `#F1F5F9`
- Text Secondary: `#94A3B8`
- Accent (Blue): `#60A5FA`
- Success (Green): `#34D399`
- Warning (Yellow): `#FBBF24`
- Danger (Red): `#F87171`

---

### Implementation

**Tailwind Config**:
```js
// tailwind.config.js
module.exports = {
  darkMode: 'class', // Use class-based dark mode
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        // ... other colors
      }
    }
  }
}
```

**CSS Variables**:
```css
/* globals.css */
:root {
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  /* ... */
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  /* ... */
}
```

**Toggle Component**:
```tsx
'use client';

export function DarkModeToggle() {
  const [isDark, setIsDark] = useState(false);

  const toggle = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <button onClick={toggle}>
      {isDark ? '☀️ Light' : '🌙 Dark'}
    </button>
  );
}
```

---

## Design System Tokens

### Typography

**Font Family**: Inter (sans-serif)

**Font Sizes**:
- `xs`: 0.75rem (12px)
- `sm`: 0.875rem (14px)
- `base`: 1rem (16px)
- `lg`: 1.125rem (18px)
- `xl`: 1.25rem (20px)
- `2xl`: 1.5rem (24px)
- `3xl`: 1.875rem (30px)
- `4xl`: 2.25rem (36px)

**Font Weights**:
- Regular: 400
- Medium: 500
- Semibold: 600
- Bold: 700

**Line Heights**:
- Tight: 1.25
- Normal: 1.5
- Relaxed: 1.75

---

### Spacing Scale

**Tailwind Default**: 4px base unit

- `1`: 0.25rem (4px)
- `2`: 0.5rem (8px)
- `3`: 0.75rem (12px)
- `4`: 1rem (16px)
- `5`: 1.25rem (20px)
- `6`: 1.5rem (24px)
- `8`: 2rem (32px)
- `10`: 2.5rem (40px)
- `12`: 3rem (48px)
- `16`: 4rem (64px)

---

### Border Radius

- `none`: 0
- `sm`: 0.125rem (2px)
- `default`: 0.25rem (4px)
- `md`: 0.375rem (6px)
- `lg`: 0.5rem (8px)
- `xl`: 0.75rem (12px)
- `full`: 9999px

---

## Component Hierarchy Example

**Dashboard Page**:
```
<AppShell>
  <NavBar>
    <Logo />
    <MonthSelector />
    <UserMenu />
  </NavBar>

  <Sidebar>
    <NavLink to="/dashboard">Dashboard</NavLink>
    <NavLink to="/transactions">Transactions</NavLink>
    <NavLink to="/cards">Cards & Rewards</NavLink>
    <NavLink to="/email">Email</NavLink>
    <NavLink to="/settings">Settings</NavLink>
  </Sidebar>

  <MainContent>
    <SpendingSummaryCard>
      <Stat label="Gross Spending" value="$2,450.00" />
      <Stat label="Total Reimbursed" value="-$450.00" />
      <Divider />
      <Stat
        label="Net Personal Spending"
        value="$2,000.00"
        tooltip={<NetSpendingCalculation />}
      />
      <CategoryBreakdown categories={categories} />
    </SpendingSummaryCard>

    <TwoColumnGrid>
      <PendingReimbursementsCard>
        <ReimbursementList items={pendingReimbursements} />
      </PendingReimbursementsCard>

      <RewardsSummaryCard>
        <CardRewardsList cards={cards} />
      </RewardsSummaryCard>
    </TwoColumnGrid>

    <RecentTransactionsCard>
      <TransactionList
        transactions={recentTransactions}
        limit={10}
      />
    </RecentTransactionsCard>
  </MainContent>
</AppShell>
```

---

## Document History

| Version | Date       | Author         | Changes                    |
|---------|------------|----------------|----------------------------|
| 1.0     | 2026-02-11 | Product/Design | Initial UI/UX design       |

---

**Questions? Contact**: product@spendi.app