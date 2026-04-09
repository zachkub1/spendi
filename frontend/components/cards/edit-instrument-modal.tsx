"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface PaymentInstrument {
  id: string;
  display_name: string;
  last_four_digits: string | null;
  network: string | null;
  issuer: string | null;
  type: string;
}

interface EditInstrumentModalProps {
  instrument: PaymentInstrument;
  onClose: () => void;
  onSuccess: (updated: PaymentInstrument) => void;
}

export function EditInstrumentModal({
  instrument,
  onClose,
  onSuccess,
}: EditInstrumentModalProps) {
  const [displayName, setDisplayName] = useState(instrument.display_name);
  const [lastFour, setLastFour] = useState(instrument.last_four_digits ?? "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCard =
    instrument.type === "credit_card" || instrument.type === "debit_card";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!displayName.trim()) {
      setError("Card name is required");
      return;
    }
    if (isCard && !/^\d{4}$/.test(lastFour)) {
      setError("Last 4 digits must be exactly 4 numbers");
      return;
    }

    try {
      setLoading(true);
      const payload: Record<string, string> = {
        display_name: displayName.trim(),
      };
      if (isCard) payload.last_four_digits = lastFour;

      const updated = await apiClient.patch<PaymentInstrument>(
        `/transactions/payment-instruments/${instrument.id}`,
        payload
      );
      onSuccess(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update card");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">Edit Card</h2>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Card Name */}
          <div>
            <label
              htmlFor="edit-name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Card Name *
            </label>
            <input
              id="edit-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
              required
            />
          </div>

          {/* Last 4 Digits (cards only) */}
          {isCard && (
            <div>
              <label
                htmlFor="edit-last4"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Last 4 Digits *
              </label>
              <input
                id="edit-last4"
                type="text"
                inputMode="numeric"
                value={lastFour}
                onChange={(e) =>
                  setLastFour(e.target.value.replace(/\D/g, "").slice(0, 4))
                }
                maxLength={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
                required
              />
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed text-sm font-medium transition-colors"
            >
              {loading ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
