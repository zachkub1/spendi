'use client';

/**
 * Email transaction list — displays ParsedTransaction cards fetched from /email/transactions.
 * Handles loading skeleton, empty state, error state, and "Load More" pagination.
 */

import { useEffect, useState } from 'react';
import type { ParsedTransaction } from '@shared/types/transaction';
import { apiClient } from '@/lib/api-client';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { getCategoryMeta } from '@/lib/category-meta';

const PAGE_SIZE = 20;

interface TransactionListProps {
  accountId?: string;
  refreshTrigger?: number;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(
    parseFloat(amount)
  );
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateString));
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function CategoryBadge({ category }: { category: string | null }) {
  if (!category) return null;
  const meta = getCategoryMeta(category);
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium capitalize ${meta.badge}`}>
      {meta.label}
    </span>
  );
}

function ParsedTransactionCard({ txn }: { txn: ParsedTransaction }) {
  // Prefer normalized merchant name; fall back to raw parser name
  const displayName = txn.merchant_normalized ?? txn.merchant_name;
  const showRawName = txn.merchant_normalized && txn.merchant_normalized !== txn.merchant_name;

  return (
    <Card className="p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        {/* Left column: merchant + metadata row */}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 truncate">{displayName}</p>
          {/* Raw parser name shown as secondary label when it differs from normalized */}
          {showRawName && (
            <p className="text-xs text-slate-400 truncate">{txn.merchant_name}</p>
          )}

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-slate-500">
            <span>{formatDate(txn.transaction_date)}</span>

            {txn.card_last_four && (
              <>
                <span aria-hidden>•</span>
                <span>••••&nbsp;{txn.card_last_four}</span>
              </>
            )}

            {txn.category && (
              <>
                <span aria-hidden>•</span>
                <CategoryBadge category={txn.category} />
              </>
            )}
          </div>
        </div>

        {/* Right column: amount + type + confidence */}
        <div className="text-right shrink-0">
          <p className="text-lg font-bold text-slate-900">{formatCurrency(txn.amount)}</p>
          <p className="text-xs text-slate-400 capitalize mt-0.5">{txn.transaction_type}</p>
          <p className="text-xs text-slate-400">{txn.confidence_score.toFixed(0)}% confident</p>
        </div>
      </div>
    </Card>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading transactions">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-20 bg-slate-100 rounded-lg animate-pulse" />
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TransactionList({ accountId, refreshTrigger }: TransactionListProps) {
  const [transactions, setTransactions] = useState<ParsedTransaction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  // Fetch a single page and optionally append to existing results
  const fetchPage = async (pageOffset: number, append: boolean) => {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String(pageOffset),
    });
    if (accountId) params.set('account_id', accountId);

    const response = await apiClient.get<{
      transactions: ParsedTransaction[];
      total: number;
    }>(`/email/transactions?${params.toString()}`);

    setTransactions(prev => (append ? [...prev, ...response.transactions] : response.transactions));
    setTotal(response.total);
  };

  // Full reset whenever accountId or refreshTrigger changes
  useEffect(() => {
    setLoading(true);
    setOffset(0);
    setError(null);

    fetchPage(0, false)
      .catch((err) => {
        console.error('Failed to fetch transactions:', err);
        setError('Failed to load transactions. Please try again.');
      })
      .finally(() => setLoading(false));
    // fetchPage is stable across renders (no external deps captured in closure)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accountId, refreshTrigger]);

  const handleLoadMore = async () => {
    const nextOffset = offset + PAGE_SIZE;
    setLoadingMore(true);
    try {
      await fetchPage(nextOffset, true);
      setOffset(nextOffset);
    } catch (err) {
      console.error('Failed to load more transactions:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const hasMore = transactions.length < total;

  // ── Render states ────────────────────────────────────���─────────────────────

  if (loading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <p className="text-lg font-medium">No transactions found</p>
        <p className="text-sm mt-1">Sync your email to discover transactions.</p>
      </div>
    );
  }

  // ── Results ────────────────────────────────────────────────────────────────

  return (
    <div>
      {/* Header: title + count */}
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">Parsed Transactions</h3>
        <span className="text-sm text-slate-500">
          {transactions.length} of {total}
        </span>
      </div>

      {/* Transaction cards */}
      <div className="space-y-3">
        {transactions.map((txn) => (
          <ParsedTransactionCard key={txn.id} txn={txn} />
        ))}
      </div>

      {/* Load-more skeleton */}
      {loadingMore && (
        <div className="mt-4">
          <LoadingSkeleton />
        </div>
      )}

      {/* Load More button */}
      {!loadingMore && hasMore && (
        <div className="mt-6 text-center">
          <Button variant="outline" onClick={handleLoadMore}>
            Load More
          </Button>
        </div>
      )}

      {/* End of results */}
      {!loadingMore && !hasMore && (
        <p className="mt-6 text-center text-sm text-slate-500">
          All {total} transaction{total !== 1 ? 's' : ''} loaded
        </p>
      )}
    </div>
  );
}
