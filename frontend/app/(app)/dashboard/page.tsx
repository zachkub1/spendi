'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { useAuth } from '@/lib/auth-context';
import { apiClient } from '@/lib/api-client';
import { getCategoryMeta } from '@/lib/category-meta';
import type { MonthlyInsightItem, NormalizedTransaction } from '@shared/types/transaction';

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

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

function fmtDate(dateStr: string): string {
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(
    new Date(dateStr)
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: 'positive' | 'negative' | 'neutral';
}) {
  const valueColor =
    highlight === 'positive'
      ? 'text-green-600'
      : highlight === 'negative'
      ? 'text-red-600'
      : 'text-slate-900';
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-5 py-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-1">{label}</p>
      <p className={`text-2xl font-bold leading-none ${valueColor}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3" aria-label="Loading">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-16 rounded-lg bg-slate-100 animate-pulse" />
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const currentYear = new Date().getFullYear();
  const currentMonth = new Date().getMonth() + 1; // 1-indexed

  const [monthly, setMonthly] = useState<MonthlyInsightItem[]>([]);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [recentTxns, setRecentTxns] = useState<NormalizedTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [monthlyData, summaryData, txnData] = await Promise.all([
        apiClient.get<MonthlyInsightItem[]>(
          `/transactions/insights/monthly?year=${currentYear}&include_demo=true`
        ),
        apiClient.get<SummaryData>('/transactions/summary?include_demo=true'),
        apiClient.get<NormalizedTransaction[]>(
          '/transactions/?limit=5&offset=0&include_demo=true'
        ),
      ]);
      setMonthly(monthlyData);
      setSummary(summaryData);
      setRecentTxns(txnData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [currentYear]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  // ── Computed stats ─────────────────────────────────────────────────────────

  const thisMonthData = monthly.find((m) => m.month === currentMonth);
  const prevMonthData = monthly.find((m) => m.month === currentMonth - 1);

  const thisMonthNet = thisMonthData ? parseFloat(thisMonthData.net) : 0;
  const prevMonthNet = prevMonthData ? parseFloat(prevMonthData.net) : 0;

  const momDelta = thisMonthNet - prevMonthNet;
  const momPercent =
    prevMonthNet !== 0 ? ((momDelta / prevMonthNet) * 100).toFixed(0) : null;

  const yearNet = monthly.reduce((s, m) => s + parseFloat(m.net), 0);
  const yearReimbursed = monthly.reduce((s, m) => s + parseFloat(m.reimbursed), 0);

  // Top 3 categories by spend (exclude payment/transfer — not discretionary)
  const topCategories = (summary?.categories ?? [])
    .filter((c) => c.category !== 'payment' && c.category !== 'transfer')
    .sort((a, b) => parseFloat(b.total_amount) - parseFloat(a.total_amount))
    .slice(0, 3);

  const hasData = summary && summary.total_transactions > 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <h1 className="text-3xl font-bold mb-1">
          Welcome back{user?.display_name ? `, ${user.display_name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm text-slate-500 mb-6">
          {new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
          })}
        </p>

        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="space-y-6">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-20 rounded-lg bg-slate-100 animate-pulse" />
              ))}
            </div>
            <LoadingSkeleton />
          </div>
        ) : !hasData ? (
          /* ── Empty state ────────────────────────────────────────────────── */
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 py-16 text-center">
            <p className="text-lg font-medium text-slate-700 mb-2">No transactions yet</p>
            <p className="text-sm text-slate-500 mb-6">
              Connect your Gmail or load demo data to get started.
            </p>
            <div className="flex justify-center gap-3">
              <Link
                href="/email"
                className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                Connect Gmail
              </Link>
              <Link
                href="/email"
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Load Demo Data
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* ── Stats row ──────────────────────────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <StatCard
                label={`Net Spent — ${currentYear}`}
                value={fmt(yearNet)}
                sub={`${fmt(yearReimbursed)} reimbursed`}
              />
              <StatCard
                label="This Month"
                value={fmt(thisMonthNet)}
                sub={`${thisMonthData?.count ?? 0} transactions`}
              />
              <StatCard
                label="vs Last Month"
                value={
                  prevMonthNet === 0
                    ? '—'
                    : `${momDelta >= 0 ? '+' : ''}${fmt(momDelta)}`
                }
                sub={momPercent ? `${momPercent}% change` : undefined}
                highlight={
                  prevMonthNet === 0
                    ? 'neutral'
                    : momDelta > 0
                    ? 'negative'
                    : 'positive'
                }
              />
              <StatCard
                label="Total Transactions"
                value={(summary?.total_transactions ?? 0).toLocaleString()}
                sub="all time"
              />
            </div>

            {/* ── Top spending categories ────────────────────────────────────── */}
            {topCategories.length > 0 && (
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-600">
                    Top Spending Categories
                  </h2>
                  <Link href="/transactions" className="text-xs text-indigo-600 hover:underline">
                    View all →
                  </Link>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {topCategories.map(({ category, count, total_amount }) => {
                    const meta = getCategoryMeta(category);
                    return (
                      <button
                        key={category}
                        onClick={() => router.push(`/transactions?category=${category}`)}
                        className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left transition-shadow hover:shadow-sm ${meta.idle}`}
                      >
                        <div>
                          <p className="font-semibold">
                            {meta.icon} {meta.label}
                          </p>
                          <p className="text-xs opacity-70 mt-0.5">{count} transactions</p>
                        </div>
                        <p className="text-lg font-bold">{fmt(parseFloat(total_amount))}</p>
                      </button>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ── Recent transactions ────────────────────────────────────────── */}
            {recentTxns.length > 0 && (
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-600">Recent Transactions</h2>
                  <Link href="/transactions" className="text-xs text-indigo-600 hover:underline">
                    View all →
                  </Link>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white divide-y divide-slate-100">
                  {recentTxns.map((txn) => {
                    const meta = getCategoryMeta(txn.category);
                    const isReimbursed =
                      txn.reimbursement_status === 'complete' ||
                      txn.reimbursement_status === 'partial';
                    return (
                      <Link
                        key={txn.id}
                        href={`/transactions/${txn.id}`}
                        className="flex items-center justify-between px-4 py-3 hover:bg-indigo-50/50 transition-colors"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-slate-900 truncate">
                            {txn.merchant_normalized}
                          </p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-slate-400">
                              {fmtDate(txn.transaction_date)}
                            </span>
                            <span
                              className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${meta.badge}`}
                            >
                              {meta.icon} {meta.label}
                            </span>
                          </div>
                        </div>
                        <div className="text-right shrink-0 ml-4">
                          <p className="font-semibold text-slate-900">
                            {fmt(parseFloat(txn.net_amount))}
                          </p>
                          {isReimbursed && (
                            <p className="text-xs text-green-600">
                              {txn.reimbursement_status === 'complete'
                                ? '✓ Reimbursed'
                                : '~ Partial'}
                            </p>
                          )}
                        </div>
                      </Link>
                    );
                  })}
                </div>
              </section>
            )}

            {/* ── Quick links ─────────────────────────────────────────────────── */}
            <section>
              <h2 className="text-sm font-semibold text-slate-600 mb-3">Quick Links</h2>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  {
                    href: '/transactions',
                    label: 'All Transactions',
                    icon: '📋',
                    sub: 'Filter, search, categorize',
                  },
                  {
                    href: '/insights',
                    label: 'Insights',
                    icon: '📈',
                    sub: 'Monthly & yearly charts',
                  },
                  {
                    href: '/email',
                    label: 'Email Sync',
                    icon: '✉️',
                    sub: 'Manage Gmail connection',
                  },
                ].map(({ href, label, icon, sub }) => (
                  <Link
                    key={href}
                    href={href}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-3 hover:shadow-sm hover:border-indigo-200 transition-all"
                  >
                    <p className="font-medium text-slate-900">
                      {icon} {label}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">{sub}</p>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
