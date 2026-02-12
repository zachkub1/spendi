'use client';

/**
 * Email integration page - manage connected Gmail accounts.
 */

import { useEffect, useState } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { ConnectGmailButton } from '@/components/email/connect-gmail-button';
import { EmailAccountCard } from '@/components/email/email-account-card';
import { SyncButton } from '@/components/email/sync-button';
import { TransactionList } from '@/components/email/transaction-list';
import type { EmailAccount } from '@shared/types/email-account';
import { apiClient } from '@/lib/api-client';
import { Separator } from '@/components/ui/separator';

export default function EmailPage() {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchAccounts = async () => {
    try {
      const response = await apiClient.get<{ accounts: EmailAccount[] }>('/email/accounts');
      setAccounts(response.accounts);
    } catch (error) {
      console.error('Failed to fetch email accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, []);

  const handleDisconnected = () => {
    fetchAccounts();
  };

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Email Integration</h1>

        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
            <p className="mt-2 text-gray-600">Loading email accounts...</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className="text-center py-12">
            <h2 className="text-xl font-semibold mb-4">No Email Accounts Connected</h2>
            <p className="text-gray-600 mb-6">
              Connect your Gmail account to automatically ingest financial transactions from email.
            </p>
            <ConnectGmailButton onConnected={fetchAccounts} />
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Connected Accounts</h2>
              <ConnectGmailButton onConnected={fetchAccounts} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              {accounts.map((account) => (
                <div key={account.id} className="space-y-2">
                  <EmailAccountCard
                    account={account}
                    onDisconnected={handleDisconnected}
                  />
                  <SyncButton
                    accountId={account.id}
                    onSyncComplete={fetchAccounts}
                  />
                </div>
              ))}
            </div>

            <Separator className="my-8" />

            <div className="mt-8">
              <TransactionList />
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
