"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { AddInstrumentModal } from "@/components/cards/add-instrument-modal";
import { EditInstrumentModal } from "@/components/cards/edit-instrument-modal";
import { apiClient } from "@/lib/api-client";
import { cardImagePath } from "@/lib/card-images";

// ─── Popular cards quick-add catalogue ────────────────────────────────────────

const POPULAR_CARDS = [
  { name: "Chase Sapphire Preferred",       issuer: "Chase",             network: "visa"       },
  { name: "Chase Sapphire Reserve",          issuer: "Chase",             network: "visa"       },
  { name: "Discover it Student",             issuer: "Discover",          network: "discover"   },
  { name: "Capital One Venture Rewards",     issuer: "Capital One",       network: "visa"       },
  { name: "American Express Gold Card",      issuer: "American Express",  network: "amex"       },
  { name: "American Express Platinum Card",  issuer: "American Express",  network: "amex"       },
  { name: "Citi Double Cash Card",           issuer: "Citi",              network: "mastercard" },
  { name: "Wells Fargo Active Cash Card",    issuer: "Wells Fargo",       network: "visa"       },
  { name: "Capital One Quicksilver",         issuer: "Capital One",       network: "visa"       },
] as const;

const NETWORK_STYLES: Record<string, string> = {
  visa:       "bg-blue-100 text-blue-700",
  mastercard: "bg-orange-100 text-orange-700",
  amex:       "bg-emerald-100 text-emerald-700",
  discover:   "bg-amber-100 text-amber-800",
};

// ─── CardArt ──────────────────────────────────────────────────────────────────
// Shows the card image from public/cards/{slug}.png when present; falls back
// to a styled placeholder so the layout never breaks.

function CardArt({ name }: { name: string }) {
  const [hasImage, setHasImage] = useState(true);

  return hasImage ? (
    <img
      src={cardImagePath(name)}
      alt={name}
      onError={() => setHasImage(false)}
      className="w-full h-20 object-cover rounded-lg mb-3"
    />
  ) : (
    <div className="w-full h-20 rounded-lg bg-slate-100 border border-dashed border-slate-300 flex items-center justify-center mb-3">
      <span className="text-xs text-slate-400">Card Art</span>
    </div>
  );
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface PaymentInstrument {
  id: string;
  type: string;
  issuer: string | null;
  display_name: string;
  last_four_digits: string | null;
  account_identifier: string | null;
  network: string | null;
  status: string;
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function CardsPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  // ── Instruments list state ───────────────────────────────────────────────
  const [instruments, setInstruments] = useState<PaymentInstrument[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  // ── P2P modal ────────────────────────────────────────────────────────────
  const [showModal, setShowModal] = useState(false);

  // ── Edit modal ────────────────────────────────────────────────────────────
  const [editingInstrument, setEditingInstrument] = useState<PaymentInstrument | null>(null);

  // ── Deactivate confirmation ───────────────────────────────────────────────
  const [pendingDeactivate, setPendingDeactivate] = useState<PaymentInstrument | null>(null);

  // ── Popular card picker ───────────────────────────────────────────────────
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);

  // ── Inline add-card form ─────────────────────────────────────────────────
  const [formName, setFormName] = useState("");
  const [formLast4, setFormLast4] = useState("");
  const [formIssuer, setFormIssuer] = useState("");
  const [formNetwork, setFormNetwork] = useState("visa");
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState(false);

  // ── Auth guard ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [authLoading, user, router]);

  // ── Fetch instruments ─────────────────────────────────────────────────────
  const fetchInstruments = async () => {
    if (!user) return;
    try {
      setListLoading(true);
      setListError(null);
      const data = await apiClient.get<PaymentInstrument[]>(
        "/transactions/payment-instruments?include_inactive=true"
      );
      setInstruments(data);
    } catch (err) {
      setListError(err instanceof Error ? err.message : "Failed to load cards");
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    fetchInstruments();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  // ── Popular card tile click ───────────────────────────────────────────────
  const handleTileClick = (idx: number) => {
    const card = POPULAR_CARDS[idx];
    setSelectedIdx(idx);
    setFormName(card.name);
    setFormIssuer(card.issuer);
    setFormNetwork(card.network);
    setFormLast4("");   // user must type their last 4
    setFormError(null);
    setFormSuccess(false);
  };

  const handleClearSelection = () => {
    setSelectedIdx(null);
    setFormName("");
    setFormLast4("");
    setFormIssuer("");
    setFormNetwork("visa");
    setFormError(null);
  };

  // ── Form submit ───────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(false);

    if (!formName.trim()) {
      setFormError("Card name is required");
      return;
    }
    if (!/^\d{4}$/.test(formLast4)) {
      setFormError("Last 4 digits must be exactly 4 numbers");
      return;
    }

    try {
      setFormLoading(true);
      await apiClient.post("/transactions/payment-instruments", {
        type: "credit_card",
        display_name: formName.trim(),
        issuer: formIssuer.trim() || null,
        last_four_digits: formLast4,
        network: formNetwork,
      });
      setFormSuccess(true);
      setFormName("");
      setFormLast4("");
      setFormIssuer("");
      setFormNetwork("visa");
      setSelectedIdx(null);
      await fetchInstruments();
      setTimeout(() => setFormSuccess(false), 3000);
    } catch (err) {
      setFormError(
        err instanceof Error ? err.message : "Failed to add card"
      );
    } finally {
      setFormLoading(false);
    }
  };

  // ── Deactivate (opens confirmation dialog) ───────────────────────────────
  const handleDeactivate = (instrument: PaymentInstrument) => {
    setPendingDeactivate(instrument);
  };

  // ── Confirm deactivate (called from dialog) ───────────────────────────────
  const confirmDeactivate = async () => {
    if (!pendingDeactivate) return;
    const { id } = pendingDeactivate;
    setPendingDeactivate(null);
    try {
      await apiClient.delete(`/transactions/payment-instruments/${id}`);
      // Update in-place — card moves to deactivated section instantly
      setInstruments((prev) =>
        prev.map((i) => (i.id === id ? { ...i, status: "inactive" } : i))
      );
    } catch {
      alert("Failed to deactivate card");
    }
  };

  // ── Reactivate ────────────────────────────────────────────────────────────
  const handleReactivate = async (id: string) => {
    try {
      const updated = await apiClient.patch<PaymentInstrument>(
        `/transactions/payment-instruments/${id}/reactivate`,
        {}
      );
      // Update in-place — card moves back to active section instantly
      setInstruments((prev) =>
        prev.map((i) => (i.id === id ? { ...i, ...updated } : i))
      );
    } catch {
      alert("Failed to reactivate card");
    }
  };

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (authLoading || !user) {
    return (
      <div className="min-h-screen bg-slate-50 p-8">
        <div className="max-w-5xl mx-auto animate-pulse space-y-8">
          <div className="h-8 bg-slate-200 rounded w-1/4" />
          <div className="grid grid-cols-3 gap-4">
            {[...Array(9)].map((_, i) => (
              <div key={i} className="h-40 bg-slate-200 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────
  const activeCards      = instruments.filter((i) => i.type !== "p2p_account" && i.status === "active");
  const deactivatedCards = instruments.filter((i) => i.type !== "p2p_account" && i.status === "inactive");
  const p2pInstruments   = instruments.filter((i) => i.type === "p2p_account" && i.status === "active");

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-5xl mx-auto space-y-10">

        {/* ── Page header ─────────────────────────────────────────────────── */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">My Cards</h1>
            <p className="mt-1 text-sm text-slate-500">
              Add and manage your credit cards
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="text-sm px-4 py-2 border border-slate-300 rounded-md text-slate-600 hover:border-indigo-400 hover:text-indigo-700 transition-colors"
          >
            + Add P2P / Debit
          </button>
        </div>

{/* ── Saved cards ──────────────────────────────────────────────────── */}
        {/* ── Active cards ─────────────────────────────────────────────── */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
            Active Cards
          </p>

          {listError && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg mb-4 text-sm text-red-800">
              {listError}
            </div>
          )}

          {listLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-32 bg-slate-100 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : activeCards.length === 0 ? (
            <div className="text-center py-10 bg-white rounded-xl border border-dashed border-slate-300">
              <p className="text-sm text-slate-500">
                No active cards — pick one from the grid below or fill in the form.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeCards.map((instrument) => (
                <Card key={instrument.id} className="p-4">
                  <CardArt name={instrument.display_name} />
                  <p className="font-semibold text-slate-900 truncate">{instrument.display_name}</p>
                  {instrument.last_four_digits && (
                    <p className="text-sm text-slate-500 mt-0.5">••••&nbsp;{instrument.last_four_digits}</p>
                  )}
                  {instrument.network && (
                    <span className={`mt-1.5 inline-block text-xs px-2 py-0.5 rounded font-medium capitalize ${NETWORK_STYLES[instrument.network] ?? "bg-slate-100 text-slate-600"}`}>
                      {instrument.network}
                    </span>
                  )}
                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => setEditingInstrument(instrument)}
                      title="Edit card"
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs bg-slate-100 text-slate-700 rounded hover:bg-slate-200 transition-colors"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M9 13l6.586-6.586a2 2 0 112.828 2.828L11.828 15.828a2 2 0 01-1.414.586H9v-2a2 2 0 01.586-1.414z" />
                      </svg>
                      Edit
                    </button>
                    <button
                      onClick={() => handleDeactivate(instrument)}
                      title="Deactivate card"
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100 transition-colors"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7h6m-7 0a1 1 0 001 1h6a1 1 0 001-1M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2" />
                      </svg>
                      Deactivate
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>

        {/* ── Deactivated cards ────────────────────────────────────────────── */}
        {!listLoading && deactivatedCards.length > 0 && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
              Deactivated Cards
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {deactivatedCards.map((instrument) => (
                <Card key={instrument.id} className="p-4 opacity-50 grayscale">
                  <CardArt name={instrument.display_name} />
                  <p className="font-semibold text-slate-900 truncate">{instrument.display_name}</p>
                  {instrument.last_four_digits && (
                    <p className="text-sm text-slate-500 mt-0.5">••••&nbsp;{instrument.last_four_digits}</p>
                  )}
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-600">
                      Deactivated
                    </span>
                  </div>
                  <button
                    onClick={() => handleReactivate(instrument.id)}
                    className="mt-4 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs bg-indigo-50 text-indigo-600 rounded hover:bg-indigo-100 transition-colors"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Reactivate
                  </button>
                </Card>
              ))}
            </div>
          </section>
        )}

        {/* ── P2P accounts ─────────────────────────────────────────────────── */}
        {p2pInstruments.length > 0 && (
          <section>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
              P2P Accounts
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {p2pInstruments.map((instrument) => (
                <Card key={instrument.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900 truncate">
                        {instrument.display_name}
                      </p>
                      {instrument.account_identifier && (
                        <p className="text-sm text-slate-500 mt-0.5 truncate">
                          {instrument.account_identifier}
                        </p>
                      )}
                    </div>
                    <span
                      className={`shrink-0 text-xs px-2 py-1 rounded ${
                        instrument.status === "active"
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-slate-500"
                      }`}
                    >
                      {instrument.status}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDeactivate(instrument)}
                    className="mt-4 w-full px-3 py-1.5 text-xs bg-red-50 text-red-600 rounded hover:bg-red-100 transition-colors"
                  >
                    Deactivate
                  </button>
                </Card>
              ))}
            </div>
          </section>
        )}
        {/* ── Popular card picker ──────────────────────────────────────────── */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
            Quick Add — Popular Cards
          </p>
          <div className="grid grid-cols-3 gap-4">
            {POPULAR_CARDS.map((card, idx) => (
              <button
                key={idx}
                onClick={() => handleTileClick(idx)}
                className={`rounded-xl border-2 p-4 text-left transition-all hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  selectedIdx === idx
                    ? "border-indigo-500 bg-indigo-50 shadow-md"
                    : "border-slate-200 bg-white hover:border-indigo-300"
                }`}
              >
                {/* Card art — shows image if file exists in public/cards/, falls back to placeholder */}
                <CardArt name={card.name} />

                <p className="text-sm font-semibold text-gray-800 leading-tight">
                  {card.name}
                </p>
                <span
                  className={`mt-1.5 inline-block text-xs px-2 py-0.5 rounded font-medium capitalize ${
                    NETWORK_STYLES[card.network] ?? "bg-slate-100 text-slate-600"
                  }`}
                >
                  {card.network}
                </span>
              </button>
            ))}
          </div>
        </section>

        {/* ── Add card form ────────────────────────────────────────────────── */}
        <section>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-4">
            {selectedIdx !== null
              ? `Adding: ${POPULAR_CARDS[selectedIdx].name}`
              : "Add a Card"}
          </p>
          <Card className="p-6 max-w-lg">
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Card name */}
              <div>
                <label
                  htmlFor="card-name"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Card Name *
                </label>
                <input
                  id="card-name"
                  type="text"
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g., Chase Sapphire Preferred"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  required
                />
                {selectedIdx !== null && (
                  <p className="mt-1 text-xs text-indigo-600">
                    Auto-filled from selection — feel free to edit
                  </p>
                )}
              </div>

              {/* Last 4 digits */}
              <div>
                <label
                  htmlFor="card-last4"
                  className="block text-sm font-medium text-slate-700 mb-1"
                >
                  Last 4 Digits *
                </label>
                <input
                  id="card-last4"
                  type="text"
                  inputMode="numeric"
                  value={formLast4}
                  onChange={(e) =>
                    setFormLast4(e.target.value.replace(/\D/g, "").slice(0, 4))
                  }
                  placeholder="1234"
                  maxLength={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  required
                />
              </div>

              {/* Feedback */}
              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-800">{formError}</p>
                </div>
              )}
              {formSuccess && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                  <p className="text-sm text-green-800">Card added successfully!</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-1">
                {selectedIdx !== null && (
                  <button
                    type="button"
                    onClick={handleClearSelection}
                    className="px-4 py-2 text-sm bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 transition-colors"
                  >
                    Clear
                  </button>
                )}
                <button
                  type="submit"
                  disabled={formLoading}
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:bg-indigo-400 disabled:cursor-not-allowed transition-colors text-sm font-medium"
                >
                  {formLoading ? "Adding…" : "Add Card"}
                </button>
              </div>
            </form>
          </Card>
        </section>
      </div>

      {/* P2P / Debit modal */}
      {showModal && (
        <AddInstrumentModal
          onClose={() => setShowModal(false)}
          onSuccess={() => {
            setShowModal(false);
            fetchInstruments();
          }}
        />
      )}

      {/* Deactivate confirmation dialog */}
      {pendingDeactivate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-6 max-w-sm w-full shadow-xl">
            <h3 className="text-lg font-semibold text-slate-900 mb-2">Deactivate Card?</h3>
            <p className="text-sm text-slate-600 mb-6">
              <strong>{pendingDeactivate.display_name}</strong> will be removed from active
              use but past transactions will remain linked.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setPendingDeactivate(null)}
                className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDeactivate}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700 transition-colors"
              >
                Deactivate
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit card modal */}
      {editingInstrument && (
        <EditInstrumentModal
          instrument={editingInstrument}
          onClose={() => setEditingInstrument(null)}
          onSuccess={(updated) => {
            // Update in-place so the grid reflects immediately without a full refetch
            setInstruments((prev) =>
              prev.map((i) => (i.id === updated.id ? { ...i, ...updated } : i))
            );
            setEditingInstrument(null);
          }}
        />
      )}
    </div>
  );
}
