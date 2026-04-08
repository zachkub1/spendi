/**
 * Canonical category display metadata for all 15 transaction categories.
 *
 * Fields:
 *   label  — human-readable name
 *   icon   — emoji for use in filter pills and dropdowns
 *   active — Tailwind classes for a selected/active filter pill
 *   idle   — Tailwind classes for an unselected filter pill (includes hover)
 *   badge  — Tailwind classes for a compact inline badge (e.g. transaction lists)
 */

export interface CategoryMeta {
  label: string;
  icon: string;
  active: string;
  idle: string;
  badge: string;
}

export const CATEGORY_META: Record<string, CategoryMeta> = {
  dining:         { label: 'Dining',         icon: '🍽️', active: 'bg-orange-500 text-white border-orange-500',  idle: 'bg-orange-50 text-orange-800 border-orange-200 hover:bg-orange-100',   badge: 'bg-orange-100 text-orange-800' },
  groceries:      { label: 'Groceries',      icon: '🛒', active: 'bg-green-600 text-white border-green-600',    idle: 'bg-green-50 text-green-800 border-green-200 hover:bg-green-100',       badge: 'bg-green-100 text-green-800' },
  gas:            { label: 'Gas',            icon: '⛽', active: 'bg-amber-500 text-white border-amber-500',    idle: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100',       badge: 'bg-amber-100 text-amber-800' },
  travel:         { label: 'Travel',         icon: '✈️', active: 'bg-blue-600 text-white border-blue-600',      idle: 'bg-blue-50 text-blue-800 border-blue-200 hover:bg-blue-100',           badge: 'bg-blue-100 text-blue-800' },
  shopping:       { label: 'Shopping',       icon: '🛍️', active: 'bg-purple-600 text-white border-purple-600',  idle: 'bg-purple-50 text-purple-800 border-purple-200 hover:bg-purple-100',   badge: 'bg-purple-100 text-purple-800' },
  entertainment:  { label: 'Entertainment',  icon: '🎬', active: 'bg-pink-600 text-white border-pink-600',      idle: 'bg-pink-50 text-pink-800 border-pink-200 hover:bg-pink-100',           badge: 'bg-pink-100 text-pink-800' },
  utilities:      { label: 'Utilities',      icon: '💡', active: 'bg-gray-600 text-white border-gray-600',      idle: 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100',           badge: 'bg-gray-100 text-gray-700' },
  healthcare:     { label: 'Healthcare',     icon: '🏥', active: 'bg-red-600 text-white border-red-600',        idle: 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100',               badge: 'bg-red-100 text-red-800' },
  transportation: { label: 'Transportation', icon: '🚗', active: 'bg-sky-600 text-white border-sky-600',        idle: 'bg-sky-50 text-sky-800 border-sky-200 hover:bg-sky-100',               badge: 'bg-sky-100 text-sky-800' },
  personal_care:  { label: 'Personal Care',  icon: '💅', active: 'bg-rose-600 text-white border-rose-600',      idle: 'bg-rose-50 text-rose-800 border-rose-200 hover:bg-rose-100',           badge: 'bg-rose-100 text-rose-800' },
  home:           { label: 'Home',           icon: '🏠', active: 'bg-teal-600 text-white border-teal-600',      idle: 'bg-teal-50 text-teal-800 border-teal-200 hover:bg-teal-100',           badge: 'bg-teal-100 text-teal-800' },
  education:      { label: 'Education',      icon: '📚', active: 'bg-indigo-600 text-white border-indigo-600',  idle: 'bg-indigo-50 text-indigo-800 border-indigo-200 hover:bg-indigo-100',   badge: 'bg-indigo-100 text-indigo-800' },
  transfer:       { label: 'Transfer',       icon: '💸', active: 'bg-slate-600 text-white border-slate-600',    idle: 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100',       badge: 'bg-slate-100 text-slate-700' },
  payment:        { label: 'Payment',        icon: '💳', active: 'bg-zinc-600 text-white border-zinc-600',      idle: 'bg-zinc-50 text-zinc-700 border-zinc-200 hover:bg-zinc-100',           badge: 'bg-zinc-100 text-zinc-700' },
  other:          { label: 'Other',          icon: '📌', active: 'bg-gray-500 text-white border-gray-500',      idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100',           badge: 'bg-gray-100 text-gray-600' },
};

/** Fallback for unknown/future categories */
export const CATEGORY_META_FALLBACK: CategoryMeta = {
  label: 'Other',
  icon: '📌',
  active: 'bg-gray-500 text-white border-gray-500',
  idle: 'bg-gray-50 text-gray-600 border-gray-200 hover:bg-gray-100',
  badge: 'bg-gray-100 text-gray-600',
};

export function getCategoryMeta(category: string): CategoryMeta {
  return CATEGORY_META[category] ?? { ...CATEGORY_META_FALLBACK, label: category.replace(/_/g, ' ') };
}
