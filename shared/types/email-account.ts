/**
 * Email account types shared between frontend and backend.
 */

export interface EmailAccount {
  id: string;
  email_address: string;
  provider: string;
  sync_enabled: boolean;
  last_sync_at: string | null;
  sync_status: 'success' | 'error' | 'in_progress' | null;
  created_at: string;
}

export interface EmailAccountListResponse {
  accounts: EmailAccount[];
}

export interface ConnectGmailResponse {
  message: string;
  account: EmailAccount;
}
