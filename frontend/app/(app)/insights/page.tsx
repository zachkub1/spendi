'use client';

import { useState, useEffect, useCallback } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { apiClient } from '@/lib/api-client';
import { SpendingChart } from '@/components/insights/spending-chart';
import { ReimbursementChart } from '@/components/insights/reimbursement-chart';
import type { MonthlyInsightItem, YearlyInsightItem, TransactionCategory } from '@shared/types/transaction';
import { CATEGORY_META, getCategoryMeta } from '@/lib/category-meta';

const ACTIVE_PILL = 'bg-indigo-700 text-white border-indigo-700';
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
    <div className="rounded-lg border border-slate-200 bg-white px-5 py-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-800 leading-none">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function InsightsPage() {
  const [year, setYear] = useState(CURRENT_YEAR);
  const [category, setCategory] = useState<TransactionCategory | ''>('');

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

      const [monthly, yearly, summary] = await Promise.all([
        apiClient.get<MonthlyInsightItem[]>(
          `/transactions/insights/monthly?year=${year}${catParam}`
        ),
        apiClient.get<YearlyInsightItem[]>(
          `/transactions/insights/yearly?${catParam}`
        ),
        apiClient.get<SummaryData>(
          `/transactions/summary`
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
  }, [year, category]);

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
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-sky-50 to-blue-100">
      <div className="container mx-auto px-4 py-8">

        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Insights</h1>
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
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Year</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {YEAR_OPTIONS.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as TransactionCategory | '')}
              className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
          <h2 className="text-sm font-semibold text-slate-600 mb-3">
            Monthly Spending — {year}
            {category && ` · ${CATEGORY_META[category]?.label ?? category}`}
          </h2>
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <SpendingChart data={monthlyData} year={year} loading={loading} />
            <p className="text-xs text-slate-400 mt-2 text-center">
              Click a bar to view transactions for that month
            </p>
          </div>
        </section>

        {/* ── Yearly summary chart ─────────────────────────────────────────── */}
        <section className="mb-8">
          <h2 className="text-sm font-semibold text-slate-600 mb-3">
            Yearly Summary
            {category && ` · ${CATEGORY_META[category]?.label ?? category}`}
          </h2>
          <div className="rounded-xl border border-slate-200 bg-white p-5">
            <ReimbursementChart data={yearlyData} loading={loading} />
            <p className="text-xs text-slate-400 mt-2 text-center">
              Click a bar to view all transactions for that year
            </p>
          </div>
        </section>

        {/* ── Category breakdown ───────────────────────────────────────────── */}
        {summaryData && summaryData.categories.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-slate-600 mb-3">
              Spending by Category (all time)
            </h2>
            <div className="flex flex-wrap gap-2">
              {summaryData.categories.map(({ category: cat, count, total_amount }) => {
                const meta = getCategoryMeta(cat);
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
      </div>
    </ProtectedRoute>
  );
}
