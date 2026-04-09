"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { apiClient } from "@/lib/api-client";

interface FilterParams {
  category?: string;
  payment_instrument_id?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}

interface PaymentInstrument {
  id: string;
  display_name: string;
  last_four_digits: string | null;
  type: string;
}

interface TransactionFiltersProps {
  filters: FilterParams;
  onFilterChange: (filters: FilterParams) => void;
  paymentInstruments?: PaymentInstrument[];
}

// Values must match the backend TransactionCategory enum (lowercase)
const CATEGORIES = [
  "dining",
  "groceries",
  "gas",
  "travel",
  "shopping",
  "entertainment",
  "utilities",
  "healthcare",
  "transportation",
  "personal_care",
  "home",
  "education",
  "transfer",
  "payment",
  "other",
];

export function TransactionFilters({
  filters,
  onFilterChange,
  paymentInstruments: instrumentsProp,
}: TransactionFiltersProps) {
  const [localFilters, setLocalFilters] = useState<FilterParams>(filters);

  // Keep local state in sync when parent changes filters externally (e.g. category card click)
  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const [fetchedInstruments, setFetchedInstruments] = useState<PaymentInstrument[]>([]);

  // Only fetch internally when the parent doesn't supply the list
  useEffect(() => {
    if (instrumentsProp !== undefined) return;
    apiClient
      .get<PaymentInstrument[]>("/transactions/payment-instruments")
      .then(setFetchedInstruments)
      .catch((err) => console.error("Error fetching payment instruments:", err));
  }, [instrumentsProp]);

  const paymentInstruments = instrumentsProp ?? fetchedInstruments;

  const handleFilterChange = (key: keyof FilterParams, value: string) => {
    const newFilters = {
      ...localFilters,
      [key]: value || undefined,
    };
    setLocalFilters(newFilters);
  };

  const handleApply = () => {
    onFilterChange(localFilters);
  };

  const handleReset = () => {
    const emptyFilters: FilterParams = {};
    setLocalFilters(emptyFilters);
    onFilterChange(emptyFilters);
  };

  return (
    <Card className="p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Filters</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Category Filter */}
        <div>
          <label
            htmlFor="category"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Category
          </label>
          <select
            id="category"
            value={localFilters.category || ""}
            onChange={(e) => handleFilterChange("category", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>

        {/* Payment Instrument Filter */}
        <div>
          <label
            htmlFor="payment_instrument"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Payment Method
          </label>
          <select
            id="payment_instrument"
            value={localFilters.payment_instrument_id || ""}
            onChange={(e) =>
              handleFilterChange("payment_instrument_id", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Payment Methods</option>
            {paymentInstruments.map((instrument) => (
              <option key={instrument.id} value={instrument.id}>
                {instrument.display_name}
                {instrument.last_four_digits && ` (••${instrument.last_four_digits})`}
              </option>
            ))}
          </select>
        </div>

        {/* Start Date Filter */}
        <div>
          <label
            htmlFor="start_date"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            Start Date
          </label>
          <input
            type="date"
            id="start_date"
            value={localFilters.start_date || ""}
            onChange={(e) => handleFilterChange("start_date", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* End Date Filter */}
        <div>
          <label
            htmlFor="end_date"
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            End Date
          </label>
          <input
            type="date"
            id="end_date"
            value={localFilters.end_date || ""}
            onChange={(e) => handleFilterChange("end_date", e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Filter Actions */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={handleApply}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          Apply Filters
        </button>
        <button
          onClick={handleReset}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
        >
          Reset
        </button>
      </div>
    </Card>
  );
}