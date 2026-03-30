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
import type { YearlyInsightItem } from '@shared/types/transaction';

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
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-lg text-sm">
      <p className="font-semibold text-gray-700 mb-2">{String(label)}</p>
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
  data: YearlyInsightItem[];
  loading: boolean;
}

export function ReimbursementChart({ data, loading }: Props) {
  const router = useRouter();

  const chartData = data.map((d) => ({
    year: d.year,
    'Net Spending': parseFloat(d.net),
    Reimbursed: parseFloat(d.reimbursed),
  }));

  // recharts v3: onClick receives MouseHandlerDataParam with activeIndex (not activePayload)
  const handleBarClick = (clickData: MouseHandlerDataParam) => {
    const idx = typeof clickData?.activeIndex === 'number' ? clickData.activeIndex : undefined;
    if (idx === undefined) return;
    const item = chartData[idx];
    if (!item) return;
    const { year } = item;
    router.push(`/transactions?start_date=${year}-01-01&end_date=${year}-12-31`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[280px] bg-gray-50 rounded-lg animate-pulse">
        <div className="h-4 w-32 bg-gray-200 rounded" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-[280px] bg-gray-50 rounded-lg border border-dashed border-gray-300">
        <p className="text-sm text-gray-400">No data yet</p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={chartData}
        margin={{ top: 4, right: 8, left: 8, bottom: 0 }}
        onClick={handleBarClick}
        style={{ cursor: 'pointer' }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="year"
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
        <Bar dataKey="Net Spending" fill="#3b82f6" radius={[3, 3, 0, 0]} maxBarSize={60} />
        <Bar dataKey="Reimbursed" fill="#22c55e" radius={[3, 3, 0, 0]} maxBarSize={60} />
      </BarChart>
    </ResponsiveContainer>
  );
}
