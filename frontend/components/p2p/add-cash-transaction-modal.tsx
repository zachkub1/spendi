"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import type { P2PTransaction } from "./p2p-tab";

interface Props {
  onClose: () => void;
  onCreated: (txn: P2PTransaction) => void;
}

const CATEGORY_OPTIONS = [
  { value: "", label: "(auto)" },
  { value: "dining", label: "Dining" },
  { value: "groceries", label: "Groceries" },
  { value: "gas", label: "Gas" },
  { value: "travel", label: "Travel" },
  { value: "shopping", label: "Shopping" },
  { value: "entertainment", label: "Entertainment" },
  { value: "transportation", label: "Transportation" },
  { value: "personal_care", label: "Personal Care" },
  { value: "home", label: "Home" },
  { value: "transfer", label: "Transfer" },
  { value: "other", label: "Other" },
];

function todayISO(): string {
  const d = new Date();
  const tz = d.getTimezoneOffset() * 60000;
  return new Date(d.getTime() - tz).toISOString().slice(0, 10);
}

export function AddCashTransactionModal({ onClose, onCreated }: Props) {
  const [kind, setKind] = useState<"spend" | "reimbursement">("spend");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [date, setDate] = useState(todayISO());
  const [category, setCategory] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0) {
      setError("Amount must be greater than zero.");
      return;
    }
    if (!description.trim()) {
      setError("Description is required.");
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        amount: parsed.toFixed(2),
        transaction_date: new Date(`${date}T12:00:00`).toISOString(),
        description: description.trim(),
        kind,
      };
      if (category) payload.category = category;

      const created = await apiClient.post<P2PTransaction>(
        "/transactions/p2p/cash",
        payload,
      );
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create cash transaction");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Add cash transaction</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Kind toggle */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Type
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setKind("spend")}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  kind === "spend"
                    ? "border-red-600 bg-red-50 text-red-700"
                    : "border-gray-300 bg-white text-gray-600 hover:border-gray-400"
                }`}
              >
                Spend
              </button>
              <button
                type="button"
                onClick={() => setKind("reimbursement")}
                className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
                  kind === "reimbursement"
                    ? "border-green-600 bg-green-50 text-green-700"
                    : "border-gray-300 bg-white text-gray-600 hover:border-gray-400"
                }`}
              >
                Reimbursement
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              {kind === "spend"
                ? "You paid cash for something."
                : "Someone paid you back in cash. You can match this to an existing expense after creating."}
            </p>
          </div>

          {/* Amount */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Amount
            </label>
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
                $
              </span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                required
                className="w-full rounded-md border border-gray-300 py-2 pl-7 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              {kind === "reimbursement" ? "From / for what" : "Description"}
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                kind === "reimbursement" ? "e.g., John — dinner reimbursement" : "e.g., Lunch with John"
              }
              required
              maxLength={255}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Date */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Category */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {CATEGORY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Adding…" : "Add"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
