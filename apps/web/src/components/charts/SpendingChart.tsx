"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useMemo } from "react";

interface SpendingChartProps {
  data: Array<{
    month: string;
    spending?: number;
    income?: number;
    spend?: number;
  }>;
  height?: number;
}

export function SpendingChart({ data, height = 300 }: SpendingChartProps) {
  const formattedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((item) => {
      // Handle both 'spending' and 'spend' field names
      const spending = Math.abs(item.spending ?? item.spend ?? 0);
      const income = Math.abs(item.income ?? 0);

      // Parse month string
      let monthLabel = item.month;
      try {
        if (item.month && item.month.length >= 7) {
          const date = new Date(item.month + "-01");
          monthLabel = date.toLocaleDateString("en-US", { month: "short" });
        }
      } catch {
        // Keep original
      }

      return {
        month: monthLabel,
        spending,
        income,
      };
    });
  }, [data]);

  if (!formattedData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formattedData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--chart-2, 142 76% 36%))" stopOpacity={0.3} />
              <stop offset="95%" stopColor="hsl(var(--chart-2, 142 76% 36%))" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorSpending" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="hsl(var(--chart-1, 0 84% 60%))" stopOpacity={0.3} />
              <stop offset="95%" stopColor="hsl(var(--chart-1, 0 84% 60%))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
            axisLine={{ stroke: "hsl(var(--border))" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload) return null;
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="font-medium mb-1">{label}</p>
                  {payload.map((entry: any) => (
                    <p
                      key={entry.name}
                      className="text-sm flex items-center gap-2"
                    >
                      <span
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: entry.color }}
                      />
                      {entry.name}: ${entry.value.toLocaleString()}
                    </p>
                  ))}
                </div>
              );
            }}
          />
          <Legend
            verticalAlign="top"
            height={36}
            iconType="circle"
            iconSize={8}
          />
          <Area
            type="monotone"
            dataKey="income"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#colorIncome)"
            name="Income"
          />
          <Area
            type="monotone"
            dataKey="spending"
            stroke="#ef4444"
            strokeWidth={2}
            fill="url(#colorSpending)"
            name="Spending"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
