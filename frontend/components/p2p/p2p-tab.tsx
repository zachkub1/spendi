"use client";

import { useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import { MatchTransactionModal } from "./match-transaction-modal";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface P2PTransaction {
  id: string;
  sender_name: string | null;
  merchant_normalized: string;
  amount: string;
  currency: string;
  transaction_date: string;
  transaction_type: string;
  p2p_source: string | null;
  p2p_transaction_id: string | null;
  category: string;
  reimbursement_status: string;
  matched_to_transaction_id: string | null;
  matched_to_transaction: {
    id: string;
    merchant_normalized: string;
    amount: string;
    transaction_date: string;
    category: string;
  } | null;
  created_at: string;
}

const CATEGORY_OPTIONS = [
  { value: "transfer", label: "Transfer" },
  { value: "payment", label: "Payment" },
  { value: "dining", label: "Dining" },
  { value: "shopping", label: "Shopping" },
  { value: "entertainment", label: "Entertainment" },
  { value: "travel", label: "Travel" },
  { value: "other", label: "Other" },
];

const HOURS_OPTIONS = [
  { value: 24, label: "Last 24 hours" },
  { value: 168, label: "Last 7 days" },
  { value: 720, label: "Last 30 days" },
  { value: 0, label: "All time" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

const fmt = (amount: string) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
    parseFloat(amount)
  );

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

// ── Component ─────────────────────────────────────────────────────────────────

interface P2PTabProps {
  source: "zelle" | "venmo";
}

export function P2PTab({ source }: P2PTabProps) {
  const [transactions, setTransactions] = useState<P2PTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [hours, setHours] = useState(24);
  const [search, setSearch] = useState("");
  const [unmatchedOnly, setUnmatchedOnly] = useState(false);

  // UI state
  const [matchingTxn, setMatchingTxn] = useState<P2PTransaction | null>(null);
  const [editingSenderTxnId, setEditingSenderTxnId] = useState<string | null>(null);
  const [senderDraft, setSenderDraft] = useState("");
  const [savingSender, setSavingSender] = useState(false);
  const [unmatchingId, setUnmatchingId] = useState<string | null>(null);
  const [typeChangeId, setTypeChangeId] = useState<string | null>(null);

  const fetchTransactions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        source,
        hours: String(hours),
        limit: "100",
      });
      if (search) params.set("search", search);
      if (unmatchedOnly) params.set("unmatched_only", "true");

      const data = await apiClient.get<P2PTransaction[]>(`/transactions/p2p/?${params}`);
      setTransactions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }, [source, hours, search, unmatchedOnly]);

  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // ── Sender rename ─────────────────────────────────────────────────────────

  const startEditSender = (txn: P2PTransaction) => {
    setEditingSenderTxnId(txn.id);
    setSenderDraft(txn.sender_name || txn.merchant_normalized);
  };

  const saveSender = async (txnId: string) => {
    setSavingSender(true);
    try {
      const updated = await apiClient.patch<P2PTransaction>(
        `/transactions/p2p/${txnId}/sender-name`,
        { sender_name: senderDraft }
      );
      setTransactions((prev) => prev.map((t) => (t.id === txnId ? updated : t)));
      setEditingSenderTxnId(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update sender name");
    } finally {
      setSavingSender(false);
    }
  };

  // ── Unmatch ───────────────────────────────────────────────────────────────

  const unmatch = async (txnId: string) => {
    setUnmatchingId(txnId);
    try {
      const updated = await apiClient.delete<P2PTransaction>(
        `/transactions/p2p/${txnId}/match`
      );
      setTransactions((prev) => prev.map((t) => (t.id === txnId ? updated : t)));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to unmatch");
    } finally {
      setUnmatchingId(null);
    }
  };

  // ── Type / category change ────────────────────────────────────────────────

  const changeType = async (txnId: string, category: string) => {
    setTypeChangeId(txnId);
    try {
      const updated = await apiClient.patch<P2PTransaction>(
        `/transactions/p2p/${txnId}/type`,
        { category }
      );
      setTransactions((prev) => prev.map((t) => (t.id === txnId ? updated : t)));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to update type");
    } finally {
      setTypeChangeId(null);
    }
  };

  // ── Source badge ──────────────────────────────────────────────────────────

  const sourceBadge =
    source === "zelle"
      ? "bg-purple-100 text-purple-700"
      : "bg-blue-100 text-blue-700";

  const sourceName = source === "zelle" ? "Zelle" : "Venmo";

  // ── Render ────────────────────────────────────────────────────────────────

  const matched = transactions.filter((t) => t.matched_to_transaction_id);
  const unmatched = transactions.filter((t) => !t.matched_to_transaction_id);

  return (
    <div className="space-y-5">
      {/* ── Toolbar ─────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400"
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search by sender, amount, or ID…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Time range */}
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {HOURS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        {/* Unmatched only toggle */}
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={unmatchedOnly}
            onChange={(e) => setUnmatchedOnly(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          Unmatched only
        </label>

        {/* Refresh */}
        <button
          onClick={fetchTransactions}
          className="px-3 py-2 text-sm border border-gray-300 rounded-md text-gray-600 hover:border-gray-400 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* ── Error ───────────────────────────────────────────────────────── */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">
          {error}
        </div>
      )}

      {/* ── Loading ─────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : transactions.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-300">
          <p className="text-sm text-gray-500">
            No {sourceName} transactions found for the selected time range.
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Try a longer time range or trigger an email sync.
          </p>
        </div>
      ) : (
        <>
          {/* ── Unmatched transactions ─────────────────────────────────── */}
          {unmatched.length > 0 && (
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
                Unmatched ({unmatched.length})
              </p>
              <div className="space-y-3">
                {unmatched.map((txn) => (
                  <TransactionRow
                    key={txn.id}
                    txn={txn}
                    sourceBadge={sourceBadge}
                    sourceName={sourceName}
                    editingSenderTxnId={editingSenderTxnId}
                    senderDraft={senderDraft}
                    setSenderDraft={setSenderDraft}
                    savingSender={savingSender}
                    unmatchingId={unmatchingId}
                    typeChangeId={typeChangeId}
                    onEditSender={startEditSender}
                    onSaveSender={saveSender}
                    onCancelEditSender={() => setEditingSenderTxnId(null)}
                    onMatch={() => setMatchingTxn(txn)}
                    onUnmatch={unmatch}
                    onTypeChange={changeType}
                  />
                ))}
              </div>
            </section>
          )}

          {/* ── Matched transactions ───────────────────────────────────── */}
          {matched.length > 0 && !unmatchedOnly && (
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
                Matched ({matched.length})
              </p>
              <div className="space-y-3">
                {matched.map((txn) => (
                  <TransactionRow
                    key={txn.id}
                    txn={txn}
                    sourceBadge={sourceBadge}
                    sourceName={sourceName}
                    editingSenderTxnId={editingSenderTxnId}
                    senderDraft={senderDraft}
                    setSenderDraft={setSenderDraft}
                    savingSender={savingSender}
                    unmatchingId={unmatchingId}
                    typeChangeId={typeChangeId}
                    onEditSender={startEditSender}
                    onSaveSender={saveSender}
                    onCancelEditSender={() => setEditingSenderTxnId(null)}
                    onMatch={() => setMatchingTxn(txn)}
                    onUnmatch={unmatch}
                    onTypeChange={changeType}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* ── Match modal ──────────────────────────────────────────────────── */}
      {matchingTxn && (
        <MatchTransactionModal
          p2pTxn={matchingTxn}
          onClose={() => setMatchingTxn(null)}
          onMatched={(updated) => {
            setTransactions((prev) =>
              prev.map((t) => (t.id === updated.id ? (updated as P2PTransaction) : t))
            );
            setMatchingTxn(null);
          }}
        />
      )}
    </div>
  );
}

// ── TransactionRow sub-component ─────────────────────────────────────────────

interface RowProps {
  txn: P2PTransaction;
  sourceBadge: string;
  sourceName: string;
  editingSenderTxnId: string | null;
  senderDraft: string;
  setSenderDraft: (v: string) => void;
  savingSender: boolean;
  unmatchingId: string | null;
  typeChangeId: string | null;
  onEditSender: (txn: P2PTransaction) => void;
  onSaveSender: (id: string) => void;
  onCancelEditSender: () => void;
  onMatch: () => void;
  onUnmatch: (id: string) => void;
  onTypeChange: (id: string, category: string) => void;
}

function TransactionRow({
  txn, sourceBadge, editingSenderTxnId, senderDraft, setSenderDraft,
  savingSender, unmatchingId, typeChangeId,
  onEditSender, onSaveSender, onCancelEditSender, onMatch, onUnmatch, onTypeChange,
}: RowProps) {
  const isMatched = Boolean(txn.matched_to_transaction_id);
  const displayName = txn.sender_name || txn.merchant_normalized;

  return (
    <div className={`bg-white rounded-xl border p-4 ${isMatched ? "border-green-200" : "border-gray-200"}`}>
      <div className="flex items-start gap-3">
        {/* Left: sender + details */}
        <div className="flex-1 min-w-0">
          {/* Sender name row */}
          {editingSenderTxnId === txn.id ? (
            <div className="flex items-center gap-2 mb-1">
              <input
                type="text"
                value={senderDraft}
                onChange={(e) => setSenderDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSaveSender(txn.id);
                  if (e.key === "Escape") onCancelEditSender();
                }}
                autoFocus
                className="flex-1 px-2 py-1 border border-blue-400 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => onSaveSender(txn.id)}
                disabled={savingSender}
                className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {savingSender ? "…" : "Save"}
              </button>
              <button
                onClick={onCancelEditSender}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 mb-0.5">
              <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
              <button
                onClick={() => onEditSender(txn)}
                title="Rename sender"
                className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828a2 2 0 01-1.414.586H9v-2a2 2 0 01.586-1.414z" />
                </svg>
              </button>
            </div>
          )}

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
            <span>{fmtDate(txn.transaction_date)}</span>
            {txn.p2p_transaction_id && (
              <span className="font-mono text-gray-400">#{txn.p2p_transaction_id}</span>
            )}
            <span className={`px-1.5 py-0.5 rounded font-medium ${sourceBadge}`}>
              {txn.p2p_source === "zelle" ? "Zelle" : "Venmo"}
            </span>
          </div>

          {/* Matched badge */}
          {isMatched && txn.matched_to_transaction && (
            <div className="mt-2 flex items-center gap-1.5 text-xs text-green-700">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span>
                Matched to{" "}
                <strong>{txn.matched_to_transaction.merchant_normalized}</strong>{" "}
                ({fmt(txn.matched_to_transaction.amount)})
              </span>
            </div>
          )}
        </div>

        {/* Right: amount + actions */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          <p className="text-base font-bold text-green-700">+{fmt(txn.amount)}</p>

          <div className="flex items-center gap-1.5">
            {/* Category dropdown */}
            <select
              value={txn.category}
              onChange={(e) => onTypeChange(txn.id, e.target.value)}
              disabled={typeChangeId === txn.id}
              title="Change type"
              className="text-xs px-2 py-1 border border-gray-300 rounded bg-white text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-500 cursor-pointer"
            >
              {CATEGORY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>

            {isMatched ? (
              <button
                onClick={() => onUnmatch(txn.id)}
                disabled={unmatchingId === txn.id}
                className="px-2.5 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50 transition-colors"
              >
                {unmatchingId === txn.id ? "…" : "Unmatch"}
              </button>
            ) : (
              <button
                onClick={onMatch}
                className="px-2.5 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Match
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
