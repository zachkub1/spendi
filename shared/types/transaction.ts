/**
 * Transaction types for email-parsed and normalized transactions.
 */

export interface ParsedTransaction {
  id: string;
  /** Raw merchant name from email parser */
  merchant_name: string;
  /** Normalized merchant name from NormalizedTransaction (null if not yet matched) */
  merchant_normalized: string | null;
  /** Decimal string, e.g. "42.50" */
  amount: string;
  transaction_date: string;
  card_last_four: string | null;
  transaction_type: string;
  confidence_score: number;
  /** Spending category from NormalizedTransaction (null if not yet matched) */
  category: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: ParsedTransaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface SyncResponse {
  message: string;
  task_id: string;
}

// ── Normalized transaction types (Phase 2+) ───────────────────────────────────

export type TransactionCategory =
  | 'dining' | 'groceries' | 'gas' | 'travel' | 'shopping'
  | 'entertainment' | 'utilities' | 'healthcare' | 'transportation'
  | 'personal_care' | 'home' | 'education' | 'transfer' | 'payment' | 'other';

export type ReimbursementStatus = 'none' | 'expected' | 'partial' | 'complete';
export type PaymentInstrumentType = 'credit_card' | 'debit_card' | 'p2p_account';
export type PaymentInstrumentStatus = 'active' | 'inactive' | 'closed';

export interface PaymentInstrument {
  id: string;
  type: PaymentInstrumentType;
  display_name: string;
  issuer: string | null;
  network: string | null;
  last_four_digits: string | null;
  account_identifier: string | null;
  status: PaymentInstrumentStatus;
  created_at: string;
  updated_at: string;
}

/** Mirrors backend TransactionResponse Pydantic schema. */
export interface NormalizedTransaction {
  id: string;
  merchant_normalized: string;
  /** JSON-serialized Decimal — use parseFloat() for display */
  amount: string;
  currency: string;
  transaction_date: string;
  transaction_type: string;
  category: TransactionCategory;
  category_confidence: number | null;
  /** "auto_rules" | "user_override" */
  category_source: string | null;
  reimbursement_status: ReimbursementStatus;
  /** JSON-serialized Decimal */
  reimbursed_amount: string;
  /** JSON-serialized Decimal */
  net_amount: string;
  /** null for transactions that couldn't be matched to a registered card */
  payment_instrument: PaymentInstrument | null;
  created_at: string;
}

/** Request body for PATCH /transactions/{id}/category */
export interface CategoryUpdateRequest {
  category: TransactionCategory;
}

// ── Insights types (Phase 3) ──────────────────────────────────────────────────

/** Monthly spending totals — mirrors MonthlyInsightItem backend schema. */
export interface MonthlyInsightItem {
  month: number;        // 1–12
  total_amount: string; // gross amount charged (Decimal string)
  reimbursed: string;   // total reimbursed (Decimal string)
  net: string;          // net spending = total_amount − reimbursed
  count: number;
}

/** Yearly spending totals — mirrors YearlyInsightItem backend schema. */
export interface YearlyInsightItem {
  year: number;
  total_amount: string;
  reimbursed: string;
  net: string;
  count: number;
}
