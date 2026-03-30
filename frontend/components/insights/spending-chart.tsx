'use client';

import { useRouter } from 'next/navigation';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  type TooltipContentProps,
  type MouseHandlerDataParam,
} from 'recharts';
import type { MonthlyInsightItem } from '@shared/types/transaction';

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function formatDollar(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
}

function formatTooltipDollar(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

// recharts v3: omit generics so defaults (ValueType, NameType) satisfy contravariant content prop
function CustomTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;
  const monthLabel = MONTH_LABELS[(label as number) - 1] ?? String(label);
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg text-sm">
      <p className="font-semibold text-gray-700 mb-2">{monthLabel}</p>
      {[...payload].map((entry) => (
        <p key={String(entry.name)} style={{ color: entry.color }} className="flex justify-between gap-4">
          <span>{String(entry.name)}</span>
          <span className="font-medium">{formatTooltipDollar(Number(entry.value) || 0)}</span>
        </p>
      ))}
    </div>
  );
}

interface Props {
  data: MonthlyInsightItem[];
  year: number;
  loading: boolean;
}

export function SpendingChart({ data, year, loading }: Props) {
  const router = useRouter();

  const chartData = data.map((d) => ({
    month: d.month,
    'Net Spending': parseFloat(d.net),
    Reimbursed: parseFloat(d.reimbursed),
  }));

  // recharts v3: onClick receives MouseHandlerDataParam with activeIndex (not activePayload)
  const handleBarClick = (clickData: MouseHandlerDataParam) => {
    const idx = typeof clickData?.activeIndex === 'number' ? clickData.activeIndex : undefined;
    if (idx === undefined) return;
    const item = chartData[idx];
    if (!item) return;
    const { month } = item;
    const start = `${year}-${String(month).padStart(2, '0')}-01`;
    const lastDay = new Date(year, month, 0).getDate();
    const end = `${year}-${String(month).padStart(2, '0')}-${lastDay}`;
    router.push(`/transactions?start_date=${start}&end_date=${end}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[320px] bg-gray-50 rounded-lg animate-pulse">
        <div className="h-4 w-32 bg-gray-200 rounded" />
      </div>
    );
  }

  const hasData = data.some((d) => parseFloat(d.net) > 0 || parseFloat(d.reimbursed) > 0);

  if (!hasData) {
    return (
      <div className="flex items-center justify-center h-[320px] bg-gray-50 rounded-lg border border-dashed border-gray-300">
        <p className="text-sm text-gray-400">No transactions for {year}</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart
        data={chartData}
        margin={{ top: 4, right: 8, left: 8, bottom: 0 }}
        onClick={handleBarClick}
        style={{ cursor: 'pointer' }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="month"
          tickFormatter={(m: number) => MONTH_LABELS[m - 1]}
          tick={{ fontSize: 12, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatDollar}
          tick={{ fontSize: 12, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          width={52}
        />
        <Tooltip content={CustomTooltip} cursor={{ fill: '#f9fafb' }} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
        />
        <Bar dataKey="Net Spending" fill="#3b82f6" radius={[3, 3, 0, 0]} maxBarSize={40} />
        <Bar dataKey="Reimbursed" fill="#22c55e" radius={[3, 3, 0, 0]} maxBarSize={40} />
      </BarChart>
    </ResponsiveContainer>
  );
}
