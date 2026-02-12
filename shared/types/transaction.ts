/**
 * Transaction types for Week 3.
 */

export interface ParsedTransaction {
  id: string;
  merchant_name: string;
  amount: string;
  transaction_date: string;
  card_last_four: string | null;
  transaction_type: string;
  confidence_score: number;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: ParsedTransaction[];
}

export interface SyncResponse {
  message: string;
  task_id: string;
}
