'use client';

import { useState, useEffect, useCallback } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { apiClient } from '@/lib/api-client';
import { TransactionList } from '@/components/transactions/transaction-list';
import { TransactionFilters } from '@/components/transactions/transaction-filters';
import { getCategoryMeta } from '@/lib/category-meta';
import { P2PTab } from '@/components/p2p/p2p-tab';

type ActiveTab = 'all' | 'zelle' | 'venmo';

// ─── Types ────────────────────────────────────────────────────────────────────

interface PaymentInstrument {
  id: string;
  display_name: string;
  last_four_digits: string | null;
  type: string;
}

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
  const [activeTab, setActiveTab] = useState<ActiveTab>('all');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  // Single unified filter state. Category card clicks update filters.category.
  const [filters, setFilters] = useState<FilterParams>({});
  const [instruments, setInstruments] = useState<PaymentInstrument[]>([]);

  const activeCategory = filters.category ?? null;

  const fetchSummary = useCallback(async () => {
    const data = await apiClient.get<SummaryData>(`/transactions/summary`);
    setSummary(data);
  }, []);

  const fetchTransactions = useCallback(
    async (newOffset: number, append: boolean, currentFilters: FilterParams) => {
      const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(newOffset) });
      if (currentFilters.category) params.set('category', currentFilters.category);
      if (currentFilters.payment_instrument_id)
        params.set('payment_instrument_id', currentFilters.payment_instrument_id);
      if (currentFilters.start_date) params.set('start_date', currentFilters.start_date);
      if (currentFilters.end_date) params.set('end_date', currentFilters.end_date);

      const data = await apiClient.get<Transaction[]>(`/transactions/?${params.toString()}`);
      setTransactions((prev) => (append ? [...prev, ...data] : data));
      setHasMore(data.length === PAGE_SIZE);
    },
    []
  );

  // Fetch payment instruments once for card chips + filter panel
  useEffect(() => {
    apiClient
      .get<PaymentInstrument[]>('/transactions/payment-instruments')
      .then(setInstruments)
      .catch((err) => console.error('[Transactions] failed to load instruments:', err));
  }, []);

  // Full reload on filter change
  useEffect(() => {
    setLoading(true);
    setOffset(0);
    setError(null);

    Promise.all([fetchSummary(), fetchTransactions(0, false, filters)])
      .catch((err) => {
        console.error('[Transactions] load failed:', err);
        setError('Failed to load transactions. Please try again.');
      })
      .finally(() => setLoading(false));
  }, [filters, fetchSummary, fetchTransactions]);

  const handleLoadMore = async () => {
    const nextOffset = offset + PAGE_SIZE;
    setLoadingMore(true);
    try {
      await fetchTransactions(nextOffset, true, filters);
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
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-sky-50 to-blue-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-3xl font-bold">Transactions</h1>
        </div>

        {/* ── Tab bar ───────────────────────────────────────────────────────── */}
        <div className="flex border-b border-slate-200 mb-6">
          {(['all', 'zelle', 'venmo'] as ActiveTab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {tab === 'all' ? 'All Transactions' : tab === 'zelle' ? 'Zelle' : 'Venmo'}
            </button>
          ))}
        </div>

        {/* ── P2P tabs ──────────────────────────────────────────────────────── */}
        {activeTab === 'zelle' && <P2PTab source="zelle" />}
        {activeTab === 'venmo' && <P2PTab source="venmo" />}

        {/* ── All Transactions tab ──────────────────────────────────────────── */}
        {activeTab === 'all' && <>

        {/* ── Category summary cards ─────────────────────────────────────────── */}
        {summary && summary.categories.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">
              Browse by Category
            </p>
            <div className="flex flex-wrap gap-2">
              {/* "All" chip */}
              <button
                onClick={() => setFilters((prev) => ({ ...prev, category: undefined }))}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                  activeCategory === null
                    ? 'bg-indigo-700 text-white border-indigo-700'
                    : 'bg-white text-slate-700 border-slate-300 hover:border-indigo-300'
                }`}
              >
                All ({summary.total_transactions})
              </button>

              {summary.categories.map(({ category, count, total_amount }) => {
                const meta = getCategoryMeta(category);
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

        {/* ── Card filter chips ──────────────────────────────────────────────── */}
        {instruments.length > 0 && (
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-3">
              Filter by Card
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setFilters((prev) => ({ ...prev, payment_instrument_id: undefined }))}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                  !filters.payment_instrument_id
                    ? 'bg-indigo-700 text-white border-indigo-700'
                    : 'bg-white text-slate-700 border-slate-300 hover:border-indigo-300'
                }`}
              >
                All Cards
              </button>
              {instruments.map((instrument) => {
                const isActive = filters.payment_instrument_id === instrument.id;
                return (
                  <button
                    key={instrument.id}
                    onClick={() =>
                      setFilters((prev) => ({
                        ...prev,
                        payment_instrument_id:
                          prev.payment_instrument_id === instrument.id
                            ? undefined
                            : instrument.id,
                      }))
                    }
                    className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-slate-700 border-slate-300 hover:border-indigo-300'
                    }`}
                  >
                    {instrument.display_name}
                    {instrument.last_four_digits && ` ••••${instrument.last_four_digits}`}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Filter panel ───────────────────────────────────────────────────── */}
        <TransactionFilters filters={filters} onFilterChange={handleFilterChange} paymentInstruments={instruments} />

        {/* ── Error ──────────────────────────────────────────────────────────── */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* ── Empty state ────────────────────────────────────────────────────── */}
        {!loading && !error && transactions.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 py-16 text-center">
            {summary?.total_transactions === 0 ? (
              <>
                <p className="text-lg font-medium text-slate-700 mb-2">No transactions yet</p>
                <p className="text-sm text-slate-500 mb-4">
                  Connect Gmail and sync your emails — transactions will appear here automatically.
                </p>
                <a
                  href="/email"
                  className="inline-block rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Go to Email Integration
                </a>
              </>
            ) : (
              <p className="text-slate-500">No transactions match the selected filters.</p>
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

        </> /* end all-transactions tab */}
      </div>
      </div>
    </ProtectedRoute>
  );
}
