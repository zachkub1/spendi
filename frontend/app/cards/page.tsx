"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { AddInstrumentModal } from "@/components/cards/add-instrument-modal";
import { apiClient } from "@/lib/api-client";

interface PaymentInstrument {
  id: string;
  type: string;
  issuer: string | null;
  display_name: string;
  last_four_digits: string | null;
  account_identifier: string | null;
  network: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export default function CardsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [instruments, setInstruments] = useState<PaymentInstrument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/login");
    }
  }, [authLoading, user, router]);

  // Fetch payment instruments
  const fetchInstruments = async () => {
    if (!user) return;

    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.get<PaymentInstrument[]>(
        "/transactions/payment-instruments"
      );
      setInstruments(data);
    } catch (err) {
      console.error("Error fetching payment instruments:", err);
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstruments();
  }, [user]);

  const handleDelete = async (id: string, displayName: string) => {
    if (
      !confirm(`Are you sure you want to deactivate ${displayName}?`)
    ) {
      return;
    }

    try {
      await apiClient.delete(`/transactions/payment-instruments/${id}`);
      // Refresh list
      await fetchInstruments();
    } catch (err) {
      console.error("Error deleting payment instrument:", err);
      alert("Failed to delete payment instrument");
    }
  };

  const handleAddSuccess = () => {
    setShowAddModal(false);
    fetchInstruments();
  };

  if (authLoading || !user) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/4 mb-8"></div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-48 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              Payment Instruments
            </h1>
            <p className="mt-2 text-gray-600">
              Manage your credit cards, debit cards, and P2P accounts
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
          >
            + Add Payment Method
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="h-48 bg-gray-100 rounded-lg animate-pulse"
              ></div>
            ))}
          </div>
        ) : instruments.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">
              No payment methods
            </h3>
            <p className="mt-2 text-gray-600">
              Add your first payment method to start tracking transactions
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
            >
              Add Payment Method
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {instruments.map((instrument) => (
              <Card key={instrument.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {instrument.type === "credit_card" && (
                        <svg
                          className="h-6 w-6 text-blue-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                          />
                        </svg>
                      )}
                      {instrument.type === "debit_card" && (
                        <svg
                          className="h-6 w-6 text-green-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"
                          />
                        </svg>
                      )}
                      {instrument.type === "p2p_account" && (
                        <svg
                          className="h-6 w-6 text-purple-600"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                          />
                        </svg>
                      )}
                      <h3 className="font-semibold text-gray-900">
                        {instrument.display_name}
                      </h3>
                    </div>

                    <div className="mt-3 space-y-1 text-sm text-gray-600">
                      {instrument.last_four_digits && (
                        <p>••••{instrument.last_four_digits}</p>
                      )}
                      {instrument.account_identifier && (
                        <p>{instrument.account_identifier}</p>
                      )}
                      {instrument.network && (
                        <p className="capitalize">{instrument.network}</p>
                      )}
                      <p className="text-xs capitalize">
                        {instrument.type.replace(/_/g, " ")}
                      </p>
                    </div>

                    <div className="mt-4 flex items-center gap-2">
                      <span
                        className={`inline-flex px-2 py-1 text-xs rounded ${
                          instrument.status === "active"
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {instrument.status}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-6 flex gap-2">
                  <button
                    onClick={() =>
                      handleDelete(instrument.id, instrument.display_name)
                    }
                    className="flex-1 px-4 py-2 text-sm bg-red-50 text-red-600 rounded-md hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 transition-colors"
                  >
                    Deactivate
                  </button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Add Instrument Modal */}
      {showAddModal && (
        <AddInstrumentModal
          onClose={() => setShowAddModal(false)}
          onSuccess={handleAddSuccess}
        />
      )}
    </div>
  );
}