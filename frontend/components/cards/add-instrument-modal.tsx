"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface AddInstrumentModalProps {
  onClose: () => void;
  onSuccess: () => void;
}

const PAYMENT_TYPES = [
  { value: "credit_card", label: "Credit Card" },
  { value: "debit_card", label: "Debit Card" },
  { value: "p2p_account", label: "P2P Account (Venmo, Zelle, etc.)" },
];

const NETWORKS = ["visa", "mastercard", "amex", "discover"];

export function AddInstrumentModal({
  onClose,
  onSuccess,
}: AddInstrumentModalProps) {
  const [type, setType] = useState<string>("credit_card");
  const [displayName, setDisplayName] = useState("");
  const [issuer, setIssuer] = useState("");
  const [lastFourDigits, setLastFourDigits] = useState("");
  const [network, setNetwork] = useState("visa");
  const [accountIdentifier, setAccountIdentifier] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isCardType = type === "credit_card" || type === "debit_card";
  const isP2PType = type === "p2p_account";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!displayName.trim()) {
      setError("Display name is required");
      return;
    }

    if (isCardType && !lastFourDigits.trim()) {
      setError("Last 4 digits are required for cards");
      return;
    }

    if (isCardType && !/^\d{4}$/.test(lastFourDigits)) {
      setError("Last 4 digits must be exactly 4 numbers");
      return;
    }

    if (isP2PType && !accountIdentifier.trim()) {
      setError("Account identifier is required for P2P accounts");
      return;
    }

    try {
      setLoading(true);

      const payload: any = {
        type,
        display_name: displayName.trim(),
        issuer: issuer.trim() || null,
      };

      if (isCardType) {
        payload.last_four_digits = lastFourDigits.trim();
        payload.network = network;
      }

      if (isP2PType) {
        payload.account_identifier = accountIdentifier.trim();
      }

      await apiClient.post("/transactions/payment-instruments", payload);
      onSuccess();
    } catch (err) {
      console.error("Error adding payment instrument:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <Card className="w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            Add Payment Method
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            disabled={loading}
          >
            <svg
              className="h-6 w-6"
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
          {/* Payment Type */}
          <div>
            <label
              htmlFor="type"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Payment Type *
            </label>
            <select
              id="type"
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            >
              {PAYMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>

          {/* Display Name */}
          <div>
            <label
              htmlFor="display_name"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Display Name *
            </label>
            <input
              type="text"
              id="display_name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g., Chase Sapphire Reserve"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
              required
            />
          </div>

          {/* Issuer */}
          <div>
            <label
              htmlFor="issuer"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Issuer
            </label>
            <input
              type="text"
              id="issuer"
              value={issuer}
              onChange={(e) => setIssuer(e.target.value)}
              placeholder="e.g., Chase, Bank of America"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading}
            />
          </div>

          {/* Card-specific fields */}
          {isCardType && (
            <>
              {/* Last 4 Digits */}
              <div>
                <label
                  htmlFor="last_four_digits"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Last 4 Digits *
                </label>
                <input
                  type="text"
                  id="last_four_digits"
                  value={lastFourDigits}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, "").slice(0, 4);
                    setLastFourDigits(value);
                  }}
                  placeholder="1234"
                  maxLength={4}
                  pattern="\d{4}"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                  required
                />
                <p className="mt-1 text-xs text-gray-500">
                  Enter the last 4 digits of your card number
                </p>
              </div>

              {/* Network */}
              <div>
                <label
                  htmlFor="network"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Network
                </label>
                <select
                  id="network"
                  value={network}
                  onChange={(e) => setNetwork(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                >
                  {NETWORKS.map((n) => (
                    <option key={n} value={n}>
                      {n.charAt(0).toUpperCase() + n.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}

          {/* P2P-specific fields */}
          {isP2PType && (
            <div>
              <label
                htmlFor="account_identifier"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Account Identifier *
              </label>
              <input
                type="text"
                id="account_identifier"
                value={accountIdentifier}
                onChange={(e) => setAccountIdentifier(e.target.value)}
                placeholder="e.g., @johndoe, john@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
                required
              />
              <p className="mt-1 text-xs text-gray-500">
                Your username, email, or phone number for this P2P account
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:bg-blue-400 disabled:cursor-not-allowed"
              disabled={loading}
            >
              {loading ? "Adding..." : "Add Payment Method"}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}