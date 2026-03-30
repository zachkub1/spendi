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
