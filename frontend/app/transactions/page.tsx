'use client';

import { useState, useEffect, useCallback } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { apiClient } from '@/lib/api-client';
import { TransactionList } from '@/components/transactions/transaction-list';
import { TransactionFilters } from '@/components/transactions/transaction-filters';

// ─── Category display metadata ────────────────────────────────────────────────

const CATEGORY_META: Record<string, { label: string; icon: string; active: string; idle: string }> = {
  dining:         { label: 'Dining',         icon: '🍽️', active: 'bg-orange-500 text-white border-orange-500',  idle: 'bg-orange-50 text-orange-800 border-orange-200 hover:bg-orange-100' },
  groceries:      { label: 'Groceries',      icon: '🛒', active: 'bg-green-600 text-white border-green-600',    idle: 'bg-green-50 text-green-800 border-green-200 hover:bg-green-100' },
  gas:            { label: 'Gas',            icon: '⛽', active: 'bg-amber-500 text-white border-amber-500',    idle: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100' },
  travel:         { label: 'Travel',         icon: '✈️', active: 'bg-blue-600 text-white border-blue-600',      idle: 'bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100' },
  shopping:       { label: 'Shopping',       icon: '🛍️', active: 'bg-purple-600 text-white border-purple-600',  idle: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100' },
  entertainment:  { label: 'Entertainment',  icon: '🎬', active: 'bg-pink-600 text-white border-pink-600',      idle: 'bg-pink-50 text-pink-800 border-pink-200 hover:bg-pink-100' },
  utilities:      { label: 'Utilities',      icon: '💡', active: 'bg-gray-600 text-white border-gray-600',      idle: 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100' },
  healthcare:     { label: 'Healthcare',     icon: '🏥', active: 'bg-red-600 text-white border-red-600',        idle: 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100' },
  transportation: { label: 'Transportation', icon: '🚗', active: 'bg-sky-600 text-white border-sky-600',        idle: 'bg-sky-50 text-sky-800 border-sky-200 hover:bg-sky-100' },
  personal_care:  { label: 'Personal Care',  icon: '💅', active: 'bg-rose-600 text-white border-rose-600',      idle: 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100' },
  home:           { label: 'Home',           icon: '🏠', active: 'bg-teal-600 text-white border-teal-600',      idle: 'bg-teal-50 text-teal-800 border-teal-200 hover:bg-teal-100' },
  education:      { label: 'Education',      icon: '📚', active: 'bg-indigo-600 text-white border-indigo-600',  idle: 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100' },
  transfer:       { label: 'Transfer',       icon: '💸', active: 'bg-slate-600 text-white border-slate-600',    idle: 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100' },
  payment:        { label: 'Payment',        icon: '💳', active: 'bg-zinc-600 text-white border-zinc-600',      idle: 'bg-zinc-50 text-zinc-700 border-zinc-200 hover:bg-zinc-100' },
  other:          { label: 'Other',          icon: '📌', active: 'bg-gray-500 text-white border-gray-500',      idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100' },
};

// ─── Types ────────────────────────────────────────────────────────────────────

interface CategorySummary {
  category: string;
  count: number;
  total_amount: string;
}

interface SummaryData {
  categories: CategorySummary[];
  total_transactions: number;
}

interface Transaction {
  id: string;
  merchant_normalized: string;
  amount: number;
  currency: string;
  transaction_date: string;
  transaction_type: string;
  category: string;
  category_confidence: number | null;
  reimbursement_status: string;
  reimbursed_amount: number;
  net_amount: number;
  payment_instrument: {
    id: string;
    display_name: string;
    last_four_digits: string | null;
    type: string;
  };
  created_at: string;
}

interface FilterParams {
  category?: string;
  payment_instrument_id?: string;
  start_date?: string;
  end_date?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PAGE_SIZE = 50;

function formatCurrency(amount: string): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(
    parseFloat(amount)
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showDemoData, setShowDemoData] = useState(true);
  // Single unified filter state. Category card clicks update filters.category.
  const [filters, setFilters] = useState<FilterParams>({});

  const activeCategory = filters.category ?? null;

  const fetchSummary = useCallback(async (includeDemo: boolean) => {
    const params = new URLSearchParams();
    if (!includeDemo) params.set('include_demo', 'false');
    const data = await apiClient.get<SummaryData>(`/transactions/summary?${params.toString()}`);
    setSummary(data);
  }, []);

  const fetchTransactions = useCallback(
    async (newOffset: number, append: boolean, currentFilters: FilterParams, includeDemo: boolean) => {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(newOffset) });
      if (currentFilters.category) params.set('category', currentFilters.category);
      if (currentFilters.payment_instrument_id)
        params.set('payment_instrument_id', currentFilters.payment_instrument_id);
      if (currentFilters.start_date) params.set('start_date', currentFilters.start_date);
      if (currentFilters.end_date) params.set('end_date', currentFilters.end_date);
      if (!includeDemo) params.set('include_demo', 'false');

      const data = await apiClient.get<Transaction[]>(`/transactions/?${params.toString()}`);
      setTransactions((prev) => (append ? [...prev, ...data] : data));
      setHasMore(data.length === PAGE_SIZE);
    },
    []
  );

  // Full reload on filter or demo-visibility change
  useEffect(() => {
    setLoading(true);
    setOffset(0);
    setError(null);

    Promise.all([fetchSummary(showDemoData), fetchTransactions(0, false, filters, showDemoData)])
      .catch((err) => {
        console.error('[Transactions] load failed:', err);
        setError('Failed to load transactions. Please try again.');
      })
      .finally(() => setLoading(false));
  }, [filters, showDemoData, fetchSummary, fetchTransactions]);

  const handleLoadMore = async () => {
    const nextOffset = offset + PAGE_SIZE;
    setLoadingMore(true);
    try {
      await fetchTransactions(nextOffset, true, filters, showDemoData);
      setOffset(nextOffset);
    } catch (err) {
      console.error('[Transactions] load more failed:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  // Toggle: clicking the active category chip clears it
  const handleCategoryCardClick = (category: string) => {
    setFilters((prev) => ({
      ...prev,
      category: prev.category === category ? undefined : category,
    }));
  };

  // Filter panel (payment instrument / dates) ��� preserves active category
  const handleFilterChange = (newFilters: FilterParams) => {
    setFilters(newFilters);
  };

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold">Transactions</h1>
          <button
            onClick={() => setShowDemoData((v) => !v)}
            className="text-xs px-3 py-1.5 rounded-full border border-dashed border-gray-400 text-gray-500 hover:border-gray-600 hover:text-gray-700 transition-colors"
          >
            {showDemoData ? 'Hide Demo Data' : 'Show Demo Data'}
          </button>
        </div>

        {/* ── Category summary cards ─────────────────────────────────────────── */}
        {summary && summary.categories.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Browse by Category
            </p>
            <div className="flex flex-wrap gap-2">
              {/* "All" chip */}
              <button
                onClick={() => setFilters((prev) => ({ ...prev, category: undefined }))}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                  activeCategory === null
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400'
                }`}
              >
                All ({summary.total_transactions})
              </button>

              {summary.categories.map(({ category, count, total_amount }) => {
                const meta = CATEGORY_META[category] ?? {
                  label: category.replace(/_/g, ' '),
                  icon: '📌',
                  active: 'bg-gray-500 text-white border-gray-500',
                  idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100',
                };
                const isActive = activeCategory === category;
                return (
                  <button
                    key={category}
                    onClick={() => handleCategoryCardClick(category)}
                    className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                      isActive ? meta.active : meta.idle
                    }`}
                  >
                    {meta.icon} {meta.label} · {count} · {formatCurrency(total_amount)}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Filter panel ───────────────────────────────────────────────────── */}
        <TransactionFilters filters={filters} onFilterChange={handleFilterChange} />

        {/* ── Error ──────────────────────────────────────────────────────────── */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* ── Empty state ────────────────────────────────────────────────────── */}
        {!loading && !error && transactions.length === 0 && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 py-16 text-center">
            {summary?.total_transactions === 0 ? (
              <>
                <p className="text-lg font-medium text-gray-700 mb-2">No transactions yet</p>
                <p className="text-sm text-gray-500">
                  Go to{' '}
                  <a href="/email" className="text-blue-600 hover:underline">
                    Email Integration
                  </a>{' '}
                  and click <strong>⚡ Load Demo Transactions</strong> to get started.
                </p>
              </>
            ) : (
              <p className="text-gray-500">No transactions match the selected filters.</p>
            )}
          </div>
        )}

        {/* ── Transaction list ───────────────────────────────────────────────── */}
        <TransactionList
          transactions={transactions}
          loading={loading}
          hasMore={hasMore && !loadingMore}
          onLoadMore={handleLoadMore}
        />
      </div>
    </ProtectedRoute>
  );
}
