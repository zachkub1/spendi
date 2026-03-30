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
import { DemoSyncButton } from '@/components/email/demo-sync-button';
import type { EmailAccount } from '@shared/types/email-account';
import { apiClient } from '@/lib/api-client';
import { Separator } from '@/components/ui/separator';

export default function EmailPage() {
  const [accounts, setAccounts] = useState<EmailAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [txRefreshTrigger, setTxRefreshTrigger] = useState(0);
  const [showDemoData, setShowDemoData] = useState(true);

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

  const handleSyncComplete = () => {
    fetchAccounts();
    setTxRefreshTrigger(n => n + 1);
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
          /* ── No accounts connected ─────────────────────────────────────── */
          <div className="space-y-8">
            <div className="text-center py-12">
              <h2 className="text-xl font-semibold mb-4">No Email Accounts Connected</h2>
              <p className="text-gray-600 mb-6">
                Connect your Gmail account to automatically ingest financial transactions from email.
              </p>
              <ConnectGmailButton onConnected={fetchAccounts} />
            </div>

            {/* Demo section visible even without a connected account */}
            <Separator />
            <div className="rounded-lg border border-dashed border-gray-300 p-6 bg-gray-50">
              <h2 className="text-lg font-semibold mb-1">Try with Demo Data</h2>
              <p className="text-sm text-gray-500 mb-4">
                No Gmail account? Load 9 realistic mock transactions to explore the UI.
              </p>
              <DemoSyncButton onSyncComplete={() => setTxRefreshTrigger(n => n + 1)} />
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-semibold">Parsed Transactions</h3>
                <button
                  onClick={() => setShowDemoData(v => !v)}
                  className="text-xs px-3 py-1.5 rounded-full border border-dashed border-gray-400 text-gray-500 hover:border-gray-600 hover:text-gray-700 transition-colors"
                >
                  {showDemoData ? 'Hide Demo Data' : 'Show Demo Data'}
                </button>
              </div>
              <TransactionList refreshTrigger={txRefreshTrigger} includeDemoData={showDemoData} />
            </div>
          </div>
        ) : (
          /* ── Accounts connected ────────────────────────────────────────── */
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
                    onSyncComplete={handleSyncComplete}
                  />
                </div>
              ))}
            </div>

            <Separator className="my-8" />

            {/* Demo data section — always available for testing */}
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Parsed Transactions</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowDemoData(v => !v)}
                  className="text-xs px-3 py-1.5 rounded-full border border-dashed border-gray-400 text-gray-500 hover:border-gray-600 hover:text-gray-700 transition-colors"
                >
                  {showDemoData ? 'Hide Demo Data' : 'Show Demo Data'}
                </button>
                <DemoSyncButton onSyncComplete={() => setTxRefreshTrigger(n => n + 1)} />
              </div>
            </div>

            <TransactionList refreshTrigger={txRefreshTrigger} includeDemoData={showDemoData} />
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
