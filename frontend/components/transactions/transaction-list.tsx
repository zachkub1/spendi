"use client";

import { Card } from "@/components/ui/card";
import Link from "next/link";

interface Transaction {
  id: string;
  merchant_normalized: string;
  amount: number;
  currency: string;
  transaction_date: string;
  transaction_type: string;
  category: string;
  category_confidence: number | null;
  reimbursement_status: string;
  reimbursed_amount: number;
  net_amount: number;
  payment_instrument: {
    id: string;
    display_name: string;
    last_four_digits: string | null;
    type: string;
  } | null;
  created_at: string;
}

interface TransactionListProps {
  transactions: Transaction[];
  loading: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
}

function getReimbursementBadge(status: string) {
  switch (status) {
    // Backend ReimbursementStatus enum uses "complete" (not "full")
    case "complete":
      return { icon: "🟢", label: "Fully Reimbursed", color: "text-green-600" };
    case "partial":
      return { icon: "🟡", label: "Partially Reimbursed", color: "text-yellow-600" };
    case "none":
      return null;
    default:
      return null;
  }
}

function formatCurrency(amount: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

function TransactionCard({ transaction }: { transaction: Transaction }) {
  const badge = getReimbursementBadge(transaction.reimbursement_status);
  const isReimbursement = transaction.transaction_type === "transfer";

  return (
    <Link href={`/transactions/${transaction.id}`}>
      <Card className="p-4 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              {badge && <span className="text-lg">{badge.icon}</span>}
              <h3 className="font-semibold text-gray-900">
                {transaction.merchant_normalized}
              </h3>
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-600">
              <span>{formatDate(transaction.transaction_date)}</span>
              <span>•</span>
              <span>
                {transaction.payment_instrument
                  ? <>
                      {transaction.payment_instrument.display_name}
                      {transaction.payment_instrument.last_four_digits &&
                        ` ••••${transaction.payment_instrument.last_four_digits}`}
                    </>
                  : <span className="italic text-gray-400">Unlinked</span>
                }
              </span>
              <span>•</span>
              <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs">
                {transaction.category.replace(/_/g, " ")}
              </span>
            </div>

            {badge && (
              <div className="mt-2 text-sm">
                <span className={badge.color}>{badge.label}</span>
                {transaction.reimbursement_status === "partial" && (
                  <span className="text-gray-600 ml-2">
                    ({formatCurrency(transaction.reimbursed_amount)} of{" "}
                    {formatCurrency(transaction.amount)})
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="text-right ml-4">
            <div
              className={`text-lg font-semibold ${
                isReimbursement ? "text-green-600" : "text-gray-900"
              }`}
            >
              {isReimbursement && "+"}
              {formatCurrency(transaction.amount, transaction.currency)}
            </div>

            {transaction.reimbursement_status !== "none" && transaction.reimbursement_status !== "expected" && (
              <div className="text-sm text-gray-600 mt-1">
                Net: {formatCurrency(transaction.net_amount, transaction.currency)}
              </div>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}

export function TransactionList({
  transactions,
  loading,
  hasMore,
  onLoadMore,
}: TransactionListProps) {
  return (
    <div>
      {/* Transaction Count */}
      {transactions.length > 0 && (
        <div className="mb-4 text-sm text-gray-600">
          Showing {transactions.length} transaction{transactions.length !== 1 && "s"}
        </div>
      )}

      {/* Transaction Cards */}
      <div className="space-y-3">
        {transactions.map((transaction) => (
          <TransactionCard key={transaction.id} transaction={transaction} />
        ))}
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="mt-6 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-24 bg-slate-100 rounded-lg animate-pulse"
            ></div>
          ))}
        </div>
      )}

      {/* Load More Button */}
      {!loading && hasMore && transactions.length > 0 && (
        <div className="mt-6 text-center">
          <button
            onClick={onLoadMore}
            className="px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
          >
            Load More
          </button>
        </div>
      )}

      {/* End of Results */}
      {!loading && !hasMore && transactions.length > 0 && (
        <div className="mt-6 text-center text-slate-500 text-sm">
          No more transactions to load
        </div>
      )}
    </div>
  );
}