"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { useMemo } from "react";

interface CategoryPieChartProps {
  data: Array<{
    name?: string;
    category?: string;
    value?: number;
    amount?: number;
    total?: number;
    spend?: number;
    color?: string;
  }>;
  height?: number;
}

const COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

export function CategoryPieChart({ data, height = 300 }: CategoryPieChartProps) {
  const formattedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    return data
      .map((item, index) => ({
        name: item.name || item.category || "Unknown",
        value: Math.abs(item.value ?? item.amount ?? item.total ?? item.spend ?? 0),
        color: item.color || COLORS[index % COLORS.length],
      }))
      .filter((item) => item.value > 0)
      .sort((a, b) => b.value - a.value)
      .slice(0, 8); // Top 8 categories
  }, [data]);

  if (!formattedData.length) {
    return (
      <div style={{ height }} className="flex items-center justify-center text-muted-foreground">
        No data available
      </div>
    );
  }

  const total = formattedData.reduce((sum, item) => sum + item.value, 0);

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={formattedData}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
          >
            {formattedData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={entry.color}
                className="transition-opacity hover:opacity-80"
              />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const data = payload[0].payload;
              const percentage = ((data.value / total) * 100).toFixed(1);
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="font-medium">{data.name}</p>
                  <p className="text-sm text-muted-foreground">
                    ${data.value.toLocaleString()} ({percentage}%)
                  </p>
                </div>
              );
            }}
          />
          <Legend
            layout="vertical"
            verticalAlign="middle"
            align="right"
            iconType="circle"
            iconSize={8}
            formatter={(value: string) => (
              <span className="text-sm text-foreground">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
