"use client";

import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";

interface P2PTransaction {
  id: string;
  sender_name: string | null;
  merchant_normalized: string;
  amount: string;
  transaction_date: string;
  p2p_source: string | null;
  p2p_transaction_id: string | null;
}

interface RecentTransaction {
  id: string;
  merchant_normalized: string;
  amount: string;
  transaction_date: string;
  category: string;
  reimbursement_status: string;
}

interface MatchTransactionModalProps {
  p2pTxn: P2PTransaction;
  onClose: () => void;
  onMatched: (updatedP2P: P2PTransaction) => void;
}

export function MatchTransactionModal({ p2pTxn, onClose, onMatched }: MatchTransactionModalProps) {
  const [transactions, setTransactions] = useState<RecentTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [matching, setMatching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTransactions = async (q: string) => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ days: "30", limit: "50" });
      if (q) params.set("search", q);
      const data = await apiClient.get<RecentTransaction[]>(
        `/transactions/p2p/recent-transactions?${params}`
      );
      setTransactions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions("");
  }, []);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => fetchTransactions(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const handleMatch = async () => {
    if (!selected) return;
    setMatching(true);
    setError(null);
    try {
      const updated = await apiClient.patch<P2PTransaction>(
        `/transactions/p2p/${p2pTxn.id}/match`,
        { target_transaction_id: selected }
      );
      onMatched(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to match transaction");
      setMatching(false);
    }
  };

  const fmt = (amount: string) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(
      parseFloat(amount)
    );
  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-5 border-b border-gray-200">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Match to Transaction</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                Select which expense{" "}
                <strong>{p2pTxn.sender_name || p2pTxn.merchant_normalized}</strong>&apos;s{" "}
                {fmt(p2pTxn.amount)} payment is reimbursing
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors mt-0.5"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="Search by merchant name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="mt-3 w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Transaction list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {loading ? (
            <div className="space-y-2 p-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : transactions.length === 0 ? (
            <div className="text-center py-10 text-sm text-gray-500">
              No transactions found in the last 30 days
            </div>
          ) : (
            transactions.map((txn) => (
              <button
                key={txn.id}
                onClick={() => setSelected(txn.id === selected ? null : txn.id)}
                className={`w-full text-left px-3 py-3 rounded-lg border transition-all ${
                  selected === txn.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {txn.merchant_normalized}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {fmtDate(txn.transaction_date)} · {txn.category}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-semibold text-gray-900">{fmt(txn.amount)}</p>
                    {txn.reimbursement_status !== "none" && (
                      <span className="text-xs text-amber-600 capitalize">
                        {txn.reimbursement_status}
                      </span>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 space-y-2">
          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">{error}</p>
          )}
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleMatch}
              disabled={!selected || matching}
              className="flex-1 px-4 py-2 text-sm bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
            >
              {matching ? "Matching…" : "Confirm Match"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
