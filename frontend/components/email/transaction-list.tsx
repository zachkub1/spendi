'use client';

/**
 * TransactionList - displays parsed transactions from emails.
 */

import { useEffect, useState } from 'react';
import type { ParsedTransaction } from '@shared/types/transaction';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface TransactionListProps {
  accountId?: string;
}

export function TransactionList({ accountId }: TransactionListProps) {
  const [transactions, setTransactions] = useState<ParsedTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchTransactions = async () => {
    try {
      const params = accountId ? `?account_id=${accountId}` : '';
      const response = await apiClient.get<{ transactions: ParsedTransaction[] }>(
        `/email/transactions${params}`
      );
      setTransactions(response.transactions);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, [accountId]);

  if (loading) {
    return <div className="text-center py-8">Loading transactions...</div>;
  }

  if (transactions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No transactions found. Sync your email to discover transactions.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold">Parsed Transactions</h3>
      {transactions.map((txn) => (
        <Card key={txn.id}>
          <CardContent className="pt-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold">{txn.merchant_name}</p>
                <p className="text-sm text-gray-500">
                  {new Date(txn.transaction_date).toLocaleDateString()}
                  {txn.card_last_four && ` • Card ****${txn.card_last_four}`}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {txn.transaction_type} • {txn.confidence_score.toFixed(0)}% confidence
                </p>
              </div>
              <div className="text-right">
                <p className="font-bold text-lg">${txn.amount}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
