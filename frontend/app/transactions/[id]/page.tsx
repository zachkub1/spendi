'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ProtectedRoute } from '@/components/auth/protected-route';
import { apiClient } from '@/lib/api-client';
import type {
  NormalizedTransaction,
  TransactionCategory,
} from '@shared/types/transaction';

// ─── Category metadata ────────────────────────────────────────────────────────

const CATEGORY_META: Record<TransactionCategory, { label: string; icon: string; color: string }> = {
  dining:         { label: 'Dining & Restaurants', icon: '🍽️',  color: 'bg-orange-100 text-orange-800' },
  groceries:      { label: 'Groceries',            icon: '🛒',  color: 'bg-green-100 text-green-800' },
  gas:            { label: 'Gas & Fuel',            icon: '⛽',  color: 'bg-amber-100 text-amber-800' },
  travel:         { label: 'Travel',                icon: '✈️',  color: 'bg-blue-100 text-blue-800' },
  shopping:       { label: 'Shopping',              icon: '🛍️',  color: 'bg-purple-100 text-purple-800' },
  entertainment:  { label: 'Entertainment',         icon: '🎬',  color: 'bg-pink-100 text-pink-800' },
  utilities:      { label: 'Utilities',             icon: '💡',  color: 'bg-gray-100 text-gray-700' },
  healthcare:     { label: 'Healthcare',            icon: '🏥',  color: 'bg-red-100 text-red-800' },
  transportation: { label: 'Transportation',        icon: '🚗',  color: 'bg-sky-100 text-sky-800' },
  personal_care:  { label: 'Personal Care',         icon: '💅',  color: 'bg-rose-100 text-rose-800' },
  home:           { label: 'Home & Garden',         icon: '🏠',  color: 'bg-teal-100 text-teal-800' },
  education:      { label: 'Education',             icon: '📚',  color: 'bg-indigo-100 text-indigo-800' },
  transfer:       { label: 'Transfer',              icon: '💸',  color: 'bg-slate-100 text-slate-700' },
  payment:        { label: 'Payment',               icon: '💳',  color: 'bg-zinc-100 text-zinc-700' },
  other:          { label: 'Other',                 icon: '📌',  color: 'bg-gray-100 text-gray-600' },
};

const ALL_CATEGORIES = Object.keys(CATEGORY_META) as TransactionCategory[];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCurrency(amount: string, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(parseFloat(amount));
}

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr));
}

function formatType(type: string): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

function getReimbursementLabel(status: string): { label: string; color: string } | null {
  switch (status) {
    case 'complete': return { label: 'Fully Reimbursed', color: 'text-green-600' };
    case 'partial':  return { label: 'Partially Reimbursed', color: 'text-yellow-600' };
    case 'expected': return { label: 'Reimbursement Expected', color: 'text-blue-600' };
    default:         return null;
  }
}

function getInstrumentIcon(type: string): string {
  switch (type) {
    case 'credit_card': return '💳';
    case 'debit_card':  return '🏦';
    case 'p2p_account': return '📱';
    default:            return '💰';
  }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function TransactionDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [transaction, setTransaction] = useState<NormalizedTransaction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [selectedCategory, setSelectedCategory] = useState<TransactionCategory | ''>('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const fetchTransaction = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<NormalizedTransaction>(`/transactions/${id}`);
      setTransaction(data);
      setSelectedCategory(data.category);
    } catch (err) {
      if (err instanceof Error && err.message.toLowerCase().includes('not found')) {
        setNotFound(true);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load transaction.');
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTransaction();
  }, [fetchTransaction]);

  const handleSaveCategory = async () => {
    if (!transaction || !selectedCategory || selectedCategory === transaction.category) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const updated = await apiClient.patch<NormalizedTransaction>(
        `/transactions/${id}/category`,
        { category: selectedCategory }
      );
      setTransaction(updated);
      setSelectedCategory(updated.category);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2500);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save category.');
    } finally {
      setSaving(false);
    }
  };

  const isDirty = selectedCategory !== '' && selectedCategory !== transaction?.category;

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute>
      <div className="container mx-auto px-4 py-8 max-w-2xl">

        {/* Back link */}
        <Link
          href="/transactions"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 mb-6 transition-colors"
        >
          ← Back to Transactions
        </Link>

        {/* Loading */}
        {loading && (
          <div className="space-y-4 animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-2/3" />
            <div className="h-5 bg-gray-200 rounded w-1/3" />
            <div className="h-px bg-gray-200 my-6" />
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-5 bg-gray-200 rounded w-full" />
              ))}
            </div>
          </div>
        )}

        {/* Not found */}
        {!loading && notFound && (
          <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 py-16 text-center">
            <p className="text-lg font-medium text-gray-700 mb-2">Transaction not found</p>
            <Link href="/transactions" className="text-sm text-blue-600 hover:underline">
              Return to transactions
            </Link>
          </div>
        )}

        {/* Fetch error */}
        {!loading && error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* Content */}
        {!loading && !error && !notFound && transaction && (() => {
          const catMeta = CATEGORY_META[transaction.category] ?? CATEGORY_META.other;
          const reimbLabel = getReimbursementLabel(transaction.reimbursement_status);
          const pi = transaction.payment_instrument;
          const netDiffers = parseFloat(transaction.net_amount) !== parseFloat(transaction.amount);

          return (
            <div className="space-y-6">

              {/* ── Header ─────────────────────────────────────────────── */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 leading-tight">
                    {transaction.merchant_normalized}
                  </h1>
                  <p className="mt-1 text-3xl font-semibold text-gray-800">
                    {formatCurrency(transaction.amount, transaction.currency)}
                    {netDiffers && (
                      <span className="ml-2 text-base font-normal text-green-600">
                        (net {formatCurrency(transaction.net_amount, transaction.currency)})
                      </span>
                    )}
                  </p>
                </div>
                <span className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium ${catMeta.color}`}>
                  {catMeta.icon} {catMeta.label}
                </span>
              </div>

              <hr className="border-gray-200" />

              {/* ── Details ────────────────────────────────────────────── */}
              <section>
                <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
                  Details
                </h2>
                <dl className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Date</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatDate(transaction.transaction_date)}
                    </dd>
                  </div>
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Payment Method</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {getInstrumentIcon(pi.type)}{' '}
                      {pi.display_name}
                      {pi.last_four_digits && (
                        <span className="text-gray-500"> ····{pi.last_four_digits}</span>
                      )}
                      {pi.account_identifier && (
                        <span className="text-gray-500"> ({pi.account_identifier})</span>
                      )}
                    </dd>
                  </div>
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Type</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatType(transaction.transaction_type)}
                    </dd>
                  </div>
                  {pi.issuer && (
                    <div className="flex px-4 py-3 bg-white">
                      <dt className="w-40 shrink-0 text-sm text-gray-500">Issuer</dt>
                      <dd className="text-sm font-medium text-gray-900">{pi.issuer}</dd>
                    </div>
                  )}
                </dl>
              </section>

              {/* ── Category ───────────────────────────────────────────── */}
              <section>
                <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
                  Category
                </h2>
                <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <select
                      value={selectedCategory}
                      onChange={(e) => setSelectedCategory(e.target.value as TransactionCategory)}
                      className="flex-1 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      {ALL_CATEGORIES.map((cat) => (
                        <option key={cat} value={cat}>
                          {CATEGORY_META[cat].icon} {CATEGORY_META[cat].label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleSaveCategory}
                      disabled={!isDirty || saving}
                      className="px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                  </div>

                  {/* Confidence / source */}
                  <p className="text-xs text-gray-400">
                    Source:{' '}
                    <span className="font-medium text-gray-600">
                      {transaction.category_source === 'user_override'
                        ? 'User override'
                        : 'Auto (rules)'}
                    </span>
                    {transaction.category_confidence != null && (
                      <>
                        {' · '}Confidence:{' '}
                        <span className="font-medium text-gray-600">
                          {Math.round(transaction.category_confidence)}%
                        </span>
                      </>
                    )}
                  </p>

                  {/* Save feedback */}
                  {saveSuccess && (
                    <p className="text-xs font-medium text-green-600">✓ Category saved</p>
                  )}
                  {saveError && (
                    <p className="text-xs font-medium text-red-600">{saveError}</p>
                  )}
                </div>
              </section>

              {/* ── Reimbursement ──────────────────────────────────────── */}
              <section>
                <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
                  Reimbursement
                </h2>
                <dl className="divide-y divide-gray-100 rounded-lg border border-gray-200 overflow-hidden">
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Status</dt>
                    <dd className={`text-sm font-medium ${reimbLabel ? reimbLabel.color : 'text-gray-900'}`}>
                      {reimbLabel ? reimbLabel.label : 'None'}
                    </dd>
                  </div>
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Reimbursed</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatCurrency(transaction.reimbursed_amount, transaction.currency)}
                    </dd>
                  </div>
                  <div className="flex px-4 py-3 bg-white">
                    <dt className="w-40 shrink-0 text-sm text-gray-500">Net Amount</dt>
                    <dd className="text-sm font-medium text-gray-900">
                      {formatCurrency(transaction.net_amount, transaction.currency)}
                    </dd>
                  </div>
                </dl>
              </section>

            </div>
          );
        })()}

      </div>
    </ProtectedRoute>
  );
}
