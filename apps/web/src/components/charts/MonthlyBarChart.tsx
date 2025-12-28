"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useMemo } from "react";

interface MonthlyBarChartProps {
  data: Array<{
    month: string;
    value?: number;
    amount?: number;
    spending?: number;
    spend?: number;
  }>;
  height?: number;
  color?: string;
  showNegative?: boolean;
}

export function MonthlyBarChart({
  data,
  height = 200,
  color = "#3b82f6",
  showNegative = false,
}: MonthlyBarChartProps) {
  const formattedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data.map((item) => {
      const value = item.value ?? item.amount ?? item.spending ?? item.spend ?? 0;

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
        value: showNegative ? value : Math.abs(value),
        isNegative: value < 0,
      };
    });
  }, [data, showNegative]);

  if (!formattedData.length) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-muted-foreground">
        No data available
      </div>
    );
  }

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={formattedData} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" opacity={0.3} vertical={false} />
          <XAxis
            dataKey="month"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.[0]) return null;
              const value = payload[0].value as number;
              return (
                <div className="rounded-lg border bg-background p-2 shadow-lg text-sm">
                  <p className="font-medium">{label}</p>
                  <p className="text-muted-foreground">
                    ${Math.abs(value).toLocaleString()}
                  </p>
                </div>
              );
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {formattedData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.isNegative ? "#ef4444" : color}
                className="transition-opacity hover:opacity-80"
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
