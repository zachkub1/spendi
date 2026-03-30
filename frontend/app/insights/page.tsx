'use client';

import { useState, useEffect, useCallback } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { apiClient } from '@/lib/api-client';
import { SpendingChart } from '@/components/insights/spending-chart';
import { ReimbursementChart } from '@/components/insights/reimbursement-chart';
import type { MonthlyInsightItem, YearlyInsightItem, TransactionCategory } from '@shared/types/transaction';

// ─── Category metadata (mirrors transactions/page.tsx) ────────────────────────

const CATEGORY_META: Record<string, { label: string; icon: string; idle: string }> = {
  dining:         { label: 'Dining',         icon: '🍽️', idle: 'bg-orange-50 text-orange-800 border-orange-200 hover:bg-orange-100' },
  groceries:      { label: 'Groceries',      icon: '🛒', idle: 'bg-green-50 text-green-800 border-green-200 hover:bg-green-100' },
  gas:            { label: 'Gas',            icon: '⛽', idle: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100' },
  travel:         { label: 'Travel',         icon: '✈️', idle: 'bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100' },
  shopping:       { label: 'Shopping',       icon: '🛍️', idle: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100' },
  entertainment:  { label: 'Entertainment',  icon: '🎬', idle: 'bg-pink-50 text-pink-800 border-pink-200 hover:bg-pink-100' },
  utilities:      { label: 'Utilities',      icon: '💡', idle: 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100' },
  healthcare:     { label: 'Healthcare',     icon: '🏥', idle: 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100' },
  transportation: { label: 'Transportation', icon: '🚗', idle: 'bg-sky-50 text-sky-800 border-sky-200 hover:bg-sky-100' },
  personal_care:  { label: 'Personal Care',  icon: '💅', idle: 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100' },
  home:           { label: 'Home',           icon: '🏠', idle: 'bg-teal-50 text-teal-800 border-teal-200 hover:bg-teal-100' },
  education:      { label: 'Education',      icon: '📚', idle: 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100' },
  transfer:       { label: 'Transfer',       icon: '💸', idle: 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100' },
  payment:        { label: 'Payment',        icon: '💳', idle: 'bg-zinc-50 text-zinc-700 border-zinc-200 hover:bg-zinc-100' },
  other:          { label: 'Other',          icon: '📌', idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100' },
};

const ACTIVE_PILL = 'bg-gray-900 text-white border-gray-900';
const ALL_CATEGORY_KEYS = Object.keys(CATEGORY_META) as TransactionCategory[];

// ─── Year range helpers ───────────────────────────────────────────────────────

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => CURRENT_YEAR - i);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(amount: number): string {
  if (amount >= 10000) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
  }
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
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

// ─── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-5 py-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900 leading-none">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [category, setCategory] = useState<TransactionCategory | ''>('');
  const [showDemo, setShowDemo] = useState(true);

  const [monthlyData, setMonthlyData] = useState<MonthlyInsightItem[]>([]);
  const [yearlyData, setYearlyData] = useState<YearlyInsightItem[]>([]);
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const catParam = category ? `&category=${category}` : '';
      const demoParam = `&include_demo=${showDemo}`;

      const [monthly, yearly, summary] = await Promise.all([
        apiClient.get<MonthlyInsightItem[]>(
          `/transactions/insights/monthly?year=${year}${catParam}${demoParam}`
        ),
        apiClient.get<YearlyInsightItem[]>(
          `/transactions/insights/yearly?${catParam}${demoParam}`
        ),
        apiClient.get<SummaryData>(
          `/transactions/summary?${demoParam}`
        ),
      ]);

      setMonthlyData(monthly);
      setYearlyData(yearly);
      setSummaryData(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load insights.');
    } finally {
      setLoading(false);
    }
  }, [year, category, showDemo]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Computed summary stats ─────────────────────────────────────────────────
  const totalNet = monthlyData.reduce((s, d) => s + parseFloat(d.net), 0);
  const totalReimbursed = monthlyData.reduce((s, d) => s + parseFloat(d.reimbursed), 0);
  const totalTransactions = monthlyData.reduce((s, d) => s + d.count, 0);
  const activeMonths = monthlyData.filter((d) => d.count > 0).length;
  const avgPerActiveMonth = activeMonths > 0 ? totalNet / activeMonths : 0;

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-3xl font-bold">Insights</h1>
          <button
            onClick={() => setShowDemo((v) => !v)}
            className="text-xs px-3 py-1.5 rounded-full border border-dashed border-gray-400 text-gray-500 hover:border-gray-600 hover:text-gray-700 transition-colors"
          >
            {showDemo ? 'Hide Demo Data' : 'Show Demo Data'}
          </button>
        </div>

        {/* ── Error ───────────────────────────────────────────────────────── */}
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* ── Summary stat cards ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatCard
            label="Net Spent"
            value={loading ? '—' : formatCurrency(totalNet)}
            sub={`${year}`}
          />
          <StatCard
            label="Reimbursed"
            value={loading ? '—' : formatCurrency(totalReimbursed)}
            sub="this year"
          />
          <StatCard
            label="Transactions"
            value={loading ? '—' : totalTransactions.toLocaleString()}
            sub={`${year}`}
          />
          <StatCard
            label="Avg / Month"
            value={loading ? '—' : formatCurrency(avgPerActiveMonth)}
            sub={activeMonths > 0 ? `${activeMonths} active month${activeMonths !== 1 ? 's' : ''}` : 'no data'}
          />
        </div>

        {/* ── Filters ─────────────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-400">Year</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {YEAR_OPTIONS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-gray-400">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as TransactionCategory | '')}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All categories</option>
              {ALL_CATEGORY_KEYS.map((cat) => (
                <option key={cat} value={cat}>
                  {CATEGORY_META[cat].icon} {CATEGORY_META[cat].label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* ── Monthly spending chart ───────────────────────────────────────── */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">
            Monthly Spending — {year}
            {category && ` · ${CATEGORY_META[category]?.label ?? category}`}
          </h2>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <SpendingChart data={monthlyData} year={year} loading={loading} />
            <p className="text-xs text-gray-400 mt-2 text-center">
              Click a bar to view transactions for that month
            </p>
          </div>
        </section>

        {/* ── Yearly summary chart ─────────────────────────────────────────── */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-gray-600 mb-3">
            Yearly Summary
            {category && ` · ${CATEGORY_META[category]?.label ?? category}`}
          </h2>
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <ReimbursementChart data={yearlyData} loading={loading} />
            <p className="text-xs text-gray-400 mt-2 text-center">
              Click a bar to view all transactions for that year
            </p>
          </div>
        </section>

        {/* ── Category breakdown ───────────────────────────────────────────── */}
        {summaryData && summaryData.categories.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-600 mb-3">
              Spending by Category (all time)
            </h2>
            <div className="flex flex-wrap gap-2">
              {summaryData.categories.map(({ category: cat, count, total_amount }) => {
                const meta = CATEGORY_META[cat] ?? {
                  label: cat.replace(/_/g, ' '),
                  icon: '📌',
                  idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100',
                };
                const isActive = category === cat;
                return (
                  <button
                    key={cat}
                    onClick={() => setCategory((prev) => (prev === cat ? '' : cat as TransactionCategory))}
                    className={`px-4 py-2 rounded-full border text-sm font-medium transition-all ${
                      isActive ? ACTIVE_PILL : meta.idle
                    }`}
                  >
                    {meta.icon} {meta.label} · {count} · {formatCurrency(parseFloat(total_amount))}
                  </button>
                );
              })}
            </div>
          </section>
        )}

      </div>
    </ProtectedRoute>
  );
}
