# KASHAT FRONTEND MODERNIZATION
## For Claude Code CLI

---

## CONTEXT

Frontend audit completed with these findings:

| Category | Score | Target |
|----------|-------|--------|
| Overall | 6.1/10 | 8.5/10 |
| UX/UI | 6.7/10 | 9.0/10 |
| 2025 Standards | 5.4/10 | 8.5/10 |
| API Health | 97% | 100% |

**Critical Issues to Fix:**
1. No mobile navigation - Sidebar hidden with no alternative
2. No charting library - Analytics lacks interactive charts
3. No dark mode - Missing system preference support
4. Missing accessibility - No ARIA labels, skip links

**Location**: `C:\Users\Marwan\Desktop\AI\Flos\apps\web`

---

## PHASE 1: MOBILE NAVIGATION (Day 1)

### 1.1 Install Dependencies

```bash
cd apps/web
npm install @radix-ui/react-dialog lucide-react
# Or if using shadcn/ui:
npx shadcn-ui@latest add sheet
```

### 1.2 Create Mobile Navigation Component

**Create**: `apps/web/src/components/layout/MobileNav.tsx`

```tsx
"use client";

import { useState } from "react";
import { Menu, X, Home, CreditCard, Calendar, PiggyBank, 
         TrendingUp, Upload, Settings, RefreshCw, ArrowLeftRight } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/budget", label: "Budget", icon: PiggyBank },
  { href: "/recurring", label: "Recurring", icon: RefreshCw },
  { href: "/transfers", label: "Transfers", icon: ArrowLeftRight },
  { href: "/analytics", label: "Analytics", icon: TrendingUp },
  { href: "/import", label: "Import", icon: Upload },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  return (
    <>
      {/* Hamburger Button - Only visible on mobile */}
      <button
        onClick={() => setIsOpen(true)}
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-background border shadow-sm"
        aria-label="Open navigation menu"
      >
        <Menu className="h-6 w-6" />
      </button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Slide-out Drawer */}
      <div
        className={cn(
          "lg:hidden fixed inset-y-0 left-0 z-50 w-72 bg-background border-r transform transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <span className="text-xl font-bold">Kashat</span>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 rounded-lg hover:bg-muted"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setIsOpen(false)}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-muted"
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </>
  );
}
```

### 1.3 Add to Layout

**Update**: `apps/web/src/app/layout.tsx`

```tsx
import { MobileNav } from "@/components/layout/MobileNav";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <MobileNav />
        {/* Existing sidebar - add lg:block hidden */}
        <aside className="hidden lg:block ...">
          {/* Existing sidebar content */}
        </aside>
        <main className="lg:pl-64 pt-16 lg:pt-0">
          {children}
        </main>
      </body>
    </html>
  );
}
```

### 1.4 Add Bottom Navigation (Mobile)

**Create**: `apps/web/src/components/layout/BottomNav.tsx`

```tsx
"use client";

import { Home, CreditCard, Calendar, TrendingUp, Menu } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const bottomNavItems = [
  { href: "/", label: "Home", icon: Home },
  { href: "/transactions", label: "Transactions", icon: CreditCard },
  { href: "/calendar", label: "Calendar", icon: Calendar },
  { href: "/analytics", label: "Analytics", icon: TrendingUp },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-background border-t z-40 pb-safe">
      <div className="flex items-center justify-around h-16">
        {bottomNavItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 px-3 py-2 text-xs",
                isActive ? "text-primary" : "text-muted-foreground"
              )}
            >
              <Icon className={cn("h-5 w-5", isActive && "text-primary")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```

### 1.5 Validation

- [ ] Hamburger menu visible on mobile (<1024px)
- [ ] Drawer slides in smoothly
- [ ] All nav items work
- [ ] Active state shows correctly
- [ ] Clicking outside closes drawer
- [ ] Bottom nav visible on mobile
- [ ] Safe area padding for iPhone notch

---

## PHASE 2: CHARTING LIBRARY (Day 1-2)

### 2.1 Install Recharts

```bash
cd apps/web
npm install recharts
```

### 2.2 Create Chart Components

**Create**: `apps/web/src/components/charts/SpendingChart.tsx`

```tsx
"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMemo } from "react";

interface SpendingChartProps {
  data: Array<{
    month: string;
    spending: number;
    income: number;
  }>;
}

export function SpendingChart({ data }: SpendingChartProps) {
  const formattedData = useMemo(() => {
    return data.map((item) => ({
      ...item,
      month: new Date(item.month + "-01").toLocaleDateString("en-US", {
        month: "short",
      }),
    }));
  }, [data]);

  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={formattedData}>
          <defs>
            <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorSpending" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
          <XAxis 
            dataKey="month" 
            className="text-xs"
            tick={{ fill: "hsl(var(--muted-foreground))" }}
          />
          <YAxis
            className="text-xs"
            tick={{ fill: "hsl(var(--muted-foreground))" }}
            tickFormatter={(value) => `$${value.toLocaleString()}`}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload) return null;
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="font-medium">{label}</p>
                  {payload.map((entry: any) => (
                    <p
                      key={entry.name}
                      className="text-sm"
                      style={{ color: entry.color }}
                    >
                      {entry.name}: ${entry.value.toLocaleString()}
                    </p>
                  ))}
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="income"
            stroke="#22c55e"
            fill="url(#colorIncome)"
            name="Income"
          />
          <Area
            type="monotone"
            dataKey="spending"
            stroke="#ef4444"
            fill="url(#colorSpending)"
            name="Spending"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Create**: `apps/web/src/components/charts/CategoryPieChart.tsx`

```tsx
"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

interface CategoryPieChartProps {
  data: Array<{
    name: string;
    value: number;
    color?: string;
  }>;
}

const COLORS = [
  "#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
];

export function CategoryPieChart({ data }: CategoryPieChartProps) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
          >
            {data.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={entry.color || COLORS[index % COLORS.length]} 
              />
            ))}
          </Pie>
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.[0]) return null;
              const data = payload[0].payload;
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="font-medium">{data.name}</p>
                  <p className="text-sm text-muted-foreground">
                    ${data.value.toLocaleString()}
                  </p>
                </div>
              );
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

**Create**: `apps/web/src/components/charts/BudgetProgressChart.tsx`

```tsx
"use client";

import { cn } from "@/lib/utils";

interface BudgetProgressChartProps {
  categories: Array<{
    name: string;
    spent: number;
    limit: number;
    color?: string;
  }>;
}

export function BudgetProgressChart({ categories }: BudgetProgressChartProps) {
  return (
    <div className="space-y-4">
      {categories.map((category) => {
        const percentage = Math.min((category.spent / category.limit) * 100, 100);
        const isOverBudget = category.spent > category.limit;

        return (
          <div key={category.name} className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{category.name}</span>
              <span className={cn(
                "text-muted-foreground",
                isOverBudget && "text-red-500 font-medium"
              )}>
                ${category.spent.toLocaleString()} / ${category.limit.toLocaleString()}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  isOverBudget ? "bg-red-500" : percentage > 80 ? "bg-yellow-500" : "bg-green-500"
                )}
                style={{ width: `${Math.min(percentage, 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

**Create**: `apps/web/src/components/charts/NetWorthChart.tsx`

```tsx
"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface NetWorthChartProps {
  data: Array<{
    date: string;
    assets: number;
    liabilities: number;
    netWorth: number;
  }>;
}

export function NetWorthChart({ data }: NetWorthChartProps) {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="netWorthGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
          />
          <YAxis 
            tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.[0]) return null;
              return (
                <div className="rounded-lg border bg-background p-3 shadow-lg">
                  <p className="font-medium">{label}</p>
                  <p className="text-sm text-blue-500">
                    Net Worth: ${payload[0].value?.toLocaleString()}
                  </p>
                </div>
              );
            }}
          />
          <Area
            type="monotone"
            dataKey="netWorth"
            stroke="#3b82f6"
            fill="url(#netWorthGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### 2.3 Create Chart Index

**Create**: `apps/web/src/components/charts/index.ts`

```ts
export { SpendingChart } from "./SpendingChart";
export { CategoryPieChart } from "./CategoryPieChart";
export { BudgetProgressChart } from "./BudgetProgressChart";
export { NetWorthChart } from "./NetWorthChart";
```

### 2.4 Update Analytics Page

**Update**: `apps/web/src/app/analytics/page.tsx`

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { SpendingChart, CategoryPieChart } from "@/components/charts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AnalyticsPage() {
  const { data: monthlyData } = useQuery({
    queryKey: ["analytics", "monthly"],
    queryFn: () => fetch("/api/analytics/spending/monthly").then(r => r.json()),
  });

  const { data: categoryData } = useQuery({
    queryKey: ["analytics", "categories"],
    queryFn: () => fetch("/api/analytics/spending/by-category").then(r => r.json()),
  });

  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-3xl font-bold">Analytics</h1>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Income vs Spending</CardTitle>
          </CardHeader>
          <CardContent>
            {monthlyData && <SpendingChart data={monthlyData} />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Spending by Category</CardTitle>
          </CardHeader>
          <CardContent>
            {categoryData && <CategoryPieChart data={categoryData} />}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

### 2.5 Validation

- [ ] All charts render without errors
- [ ] Charts are responsive
- [ ] Tooltips work
- [ ] Colors are consistent with theme
- [ ] Data loads correctly

---

## PHASE 3: DARK MODE (Day 2)

### 3.1 Install next-themes

```bash
cd apps/web
npm install next-themes
```

### 3.2 Create Theme Provider

**Create**: `apps/web/src/components/providers/ThemeProvider.tsx`

```tsx
"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import { type ThemeProviderProps } from "next-themes/dist/types";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

### 3.3 Create Theme Toggle

**Create**: `apps/web/src/components/ui/ThemeToggle.tsx`

```tsx
"use client";

import { Moon, Sun, Monitor } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) return null;

  return (
    <div className="flex items-center gap-1 p-1 rounded-lg bg-muted">
      <button
        onClick={() => setTheme("light")}
        className={`p-2 rounded-md transition-colors ${
          theme === "light" ? "bg-background shadow-sm" : "hover:bg-background/50"
        }`}
        aria-label="Light mode"
      >
        <Sun className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme("dark")}
        className={`p-2 rounded-md transition-colors ${
          theme === "dark" ? "bg-background shadow-sm" : "hover:bg-background/50"
        }`}
        aria-label="Dark mode"
      >
        <Moon className="h-4 w-4" />
      </button>
      <button
        onClick={() => setTheme("system")}
        className={`p-2 rounded-md transition-colors ${
          theme === "system" ? "bg-background shadow-sm" : "hover:bg-background/50"
        }`}
        aria-label="System theme"
      >
        <Monitor className="h-4 w-4" />
      </button>
    </div>
  );
}
```

### 3.4 Update Root Layout

**Update**: `apps/web/src/app/layout.tsx`

```tsx
import { ThemeProvider } from "@/components/providers/ThemeProvider";

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          {/* Rest of layout */}
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### 3.5 Update Tailwind Config

**Update**: `apps/web/tailwind.config.js`

```js
module.exports = {
  darkMode: "class",
  // ... rest of config
};
```

### 3.6 Update CSS Variables

**Update**: `apps/web/src/app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 221.2 83.2% 53.3%;
    --radius: 0.5rem;
    
    /* Finance specific */
    --income: 142.1 76.2% 36.3%;
    --expense: 0 84.2% 60.2%;
    --transfer: 221.2 83.2% 53.3%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 217.2 91.2% 59.8%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 224.3 76.3% 48%;
    
    /* Finance specific - dark */
    --income: 142.1 70.6% 45.3%;
    --expense: 0 72.2% 50.6%;
    --transfer: 217.2 91.2% 59.8%;
  }
}
```

### 3.7 Add Theme Toggle to Header/Settings

Add the ThemeToggle component to the settings page or header.

### 3.8 Validation

- [ ] System preference detected
- [ ] Manual toggle works
- [ ] All pages render correctly in dark mode
- [ ] Charts adapt to theme
- [ ] No flash of wrong theme on load
- [ ] Preference persisted

---

## PHASE 4: ACCESSIBILITY (Day 2-3)

### 4.1 Add Skip Link

**Update**: `apps/web/src/app/layout.tsx`

```tsx
<body>
  {/* Skip link - first focusable element */}
  <a
    href="#main-content"
    className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md"
  >
    Skip to main content
  </a>
  
  {/* Rest of layout */}
  <main id="main-content">
    {children}
  </main>
</body>
```

### 4.2 Add ARIA Labels to Navigation

**Update sidebar and mobile nav:**

```tsx
<nav aria-label="Main navigation">
  <ul role="list">
    {navItems.map((item) => (
      <li key={item.href}>
        <Link
          href={item.href}
          aria-current={pathname === item.href ? "page" : undefined}
        >
          ...
        </Link>
      </li>
    ))}
  </ul>
</nav>
```

### 4.3 Add ARIA to Interactive Components

**Buttons:**
```tsx
<button aria-label="Close dialog" aria-pressed={isOpen}>
```

**Modals:**
```tsx
<div 
  role="dialog" 
  aria-modal="true" 
  aria-labelledby="dialog-title"
>
  <h2 id="dialog-title">Dialog Title</h2>
</div>
```

**Tables:**
```tsx
<table aria-label="Transaction list">
  <thead>
    <tr>
      <th scope="col">Date</th>
      <th scope="col">Description</th>
      <th scope="col">Amount</th>
    </tr>
  </thead>
</table>
```

**Loading states:**
```tsx
<div role="status" aria-live="polite">
  <span className="sr-only">Loading...</span>
  <Spinner />
</div>
```

### 4.4 Add Keyboard Navigation

**Focus trap for modals:**
```bash
npm install focus-trap-react
```

```tsx
import FocusTrap from "focus-trap-react";

<FocusTrap active={isOpen}>
  <div className="modal">
    {/* Modal content */}
  </div>
</FocusTrap>
```

**Keyboard shortcuts:**

**Create**: `apps/web/src/hooks/useKeyboardShortcuts.ts`

```ts
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export function useKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Don't trigger in input fields
      if (
        event.target instanceof HTMLInputElement ||
        event.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      // Cmd/Ctrl + K for search
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        // Open search modal
      }

      // G + D for dashboard
      if (event.key === "g") {
        const next = (e: KeyboardEvent) => {
          if (e.key === "d") router.push("/");
          if (e.key === "t") router.push("/transactions");
          if (e.key === "a") router.push("/analytics");
          if (e.key === "b") router.push("/budget");
          window.removeEventListener("keydown", next);
        };
        window.addEventListener("keydown", next, { once: true });
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router]);
}
```

### 4.5 Create Accessible Amount Display

**Create**: `apps/web/src/components/ui/Amount.tsx`

```tsx
interface AmountProps {
  value: number;
  currency?: string;
  showSign?: boolean;
}

export function Amount({ value, currency = "USD", showSign = true }: AmountProps) {
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(Math.abs(value));

  const isNegative = value < 0;
  const sign = showSign ? (isNegative ? "-" : "+") : "";
  const label = `${isNegative ? "expense" : "income"} of ${formatted}`;

  return (
    <span
      className={isNegative ? "text-red-500" : "text-green-500"}
      aria-label={label}
    >
      {sign}{formatted}
    </span>
  );
}
```

### 4.6 Validation

- [ ] Tab navigation works through all elements
- [ ] Focus visible on all interactive elements
- [ ] Skip link works
- [ ] Screen reader announces content correctly
- [ ] Color contrast meets WCAG AA
- [ ] All images have alt text
- [ ] Form errors announced

---

## PHASE 5: UI POLISH (Day 3-4)

### 5.1 Add Loading Skeletons

**Create**: `apps/web/src/components/ui/Skeleton.tsx`

```tsx
import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted",
        className
      )}
    />
  );
}

export function TransactionSkeleton() {
  return (
    <div className="flex items-center gap-4 p-4">
      <Skeleton className="h-10 w-10 rounded-full" />
      <div className="space-y-2 flex-1">
        <Skeleton className="h-4 w-[200px]" />
        <Skeleton className="h-3 w-[100px]" />
      </div>
      <Skeleton className="h-4 w-[80px]" />
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border bg-card p-6 space-y-4">
      <Skeleton className="h-4 w-[100px]" />
      <Skeleton className="h-8 w-[150px]" />
      <Skeleton className="h-[200px] w-full" />
    </div>
  );
}
```

### 5.2 Add Toast Notifications

```bash
npm install sonner
```

**Update layout:**
```tsx
import { Toaster } from "sonner";

<body>
  {children}
  <Toaster position="bottom-right" richColors />
</body>
```

**Usage:**
```tsx
import { toast } from "sonner";

// Success
toast.success("Transaction categorized");

// Error
toast.error("Failed to import file");

// Loading
toast.loading("Importing transactions...");
```

### 5.3 Add Empty States

**Create**: `apps/web/src/components/ui/EmptyState.tsx`

```tsx
import { LucideIcon } from "lucide-react";

interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {description}
      </p>
      {action}
    </div>
  );
}
```

### 5.4 Add Micro-interactions

**Create**: `apps/web/src/components/ui/AnimatedNumber.tsx`

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  formatter?: (value: number) => string;
}

export function AnimatedNumber({
  value,
  duration = 1000,
  formatter = (v) => v.toLocaleString(),
}: AnimatedNumberProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const startTime = useRef<number | null>(null);
  const startValue = useRef(0);

  useEffect(() => {
    startValue.current = displayValue;
    startTime.current = null;

    const animate = (timestamp: number) => {
      if (!startTime.current) startTime.current = timestamp;
      const progress = Math.min((timestamp - startTime.current) / duration, 1);
      
      // Easing function
      const easeOut = 1 - Math.pow(1 - progress, 3);
      
      setDisplayValue(
        startValue.current + (value - startValue.current) * easeOut
      );

      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };

    requestAnimationFrame(animate);
  }, [value, duration]);

  return <span>{formatter(displayValue)}</span>;
}
```

### 5.5 Improve Card Design

**Update**: `apps/web/src/components/ui/Card.tsx`

```tsx
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "elevated" | "bordered";
}

export function Card({ className, variant = "default", ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-card text-card-foreground",
        variant === "default" && "border",
        variant === "elevated" && "shadow-lg border-0",
        variant === "bordered" && "border-2",
        className
      )}
      {...props}
    />
  );
}
```

### 5.6 Add Command Palette (⌘K)

```bash
npm install cmdk
```

**Create**: `apps/web/src/components/CommandPalette.tsx`

```tsx
"use client";

import { useEffect, useState } from "react";
import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { 
  Home, CreditCard, Calendar, PiggyBank, TrendingUp, 
  Upload, Settings, Search 
} from "lucide-react";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = (command: () => void) => {
    setOpen(false);
    command();
  };

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]"
    >
      <div className="fixed inset-0 bg-black/50" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg rounded-xl border bg-background shadow-2xl">
        <Command.Input
          placeholder="Type a command or search..."
          className="w-full border-b bg-transparent px-4 py-3 outline-none"
        />
        <Command.List className="max-h-[300px] overflow-y-auto p-2">
          <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
            No results found.
          </Command.Empty>

          <Command.Group heading="Navigation">
            <Command.Item onSelect={() => runCommand(() => router.push("/"))}>
              <Home className="mr-2 h-4 w-4" />
              Dashboard
            </Command.Item>
            <Command.Item onSelect={() => runCommand(() => router.push("/transactions"))}>
              <CreditCard className="mr-2 h-4 w-4" />
              Transactions
            </Command.Item>
            <Command.Item onSelect={() => runCommand(() => router.push("/analytics"))}>
              <TrendingUp className="mr-2 h-4 w-4" />
              Analytics
            </Command.Item>
            <Command.Item onSelect={() => runCommand(() => router.push("/budget"))}>
              <PiggyBank className="mr-2 h-4 w-4" />
              Budget
            </Command.Item>
            <Command.Item onSelect={() => runCommand(() => router.push("/calendar"))}>
              <Calendar className="mr-2 h-4 w-4" />
              Calendar
            </Command.Item>
          </Command.Group>

          <Command.Group heading="Actions">
            <Command.Item onSelect={() => runCommand(() => router.push("/import"))}>
              <Upload className="mr-2 h-4 w-4" />
              Import Statement
            </Command.Item>
            <Command.Item onSelect={() => runCommand(() => router.push("/settings"))}>
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Command.Item>
          </Command.Group>
        </Command.List>
        <div className="border-t px-4 py-2 text-xs text-muted-foreground">
          <kbd className="rounded bg-muted px-1">↑↓</kbd> Navigate
          <kbd className="ml-2 rounded bg-muted px-1">↵</kbd> Select
          <kbd className="ml-2 rounded bg-muted px-1">esc</kbd> Close
        </div>
      </div>
    </Command.Dialog>
  );
}
```

---

## PHASE 6: DASHBOARD REDESIGN (Day 4-5)

### 6.1 New Dashboard Layout

**Update**: `apps/web/src/app/page.tsx`

```tsx
"use client";

import { useQuery } from "@tanstack/react-query";
import { NetWorthCard } from "@/components/dashboard/NetWorthCard";
import { CashFlowCard } from "@/components/dashboard/CashFlowCard";
import { BudgetOverview } from "@/components/dashboard/BudgetOverview";
import { InsightCards } from "@/components/dashboard/InsightCards";
import { UpcomingBills } from "@/components/dashboard/UpcomingBills";
import { RecentTransactions } from "@/components/dashboard/RecentTransactions";
import { SpendingChart } from "@/components/charts";
import { CardSkeleton } from "@/components/ui/Skeleton";

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["stats"],
    queryFn: () => fetch("/api/stats").then(r => r.json()),
  });

  return (
    <div className="container mx-auto p-4 lg:p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's your financial overview.
          </p>
        </div>
      </div>

      {/* Top Row - Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <NetWorthCard />
        <CashFlowCard />
        <BudgetOverview />
      </div>

      {/* Insights Feed */}
      <InsightCards />

      {/* Middle Row - Charts and Bills */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <SpendingChartCard />
        </div>
        <UpcomingBills />
      </div>

      {/* Bottom Row - Recent Activity */}
      <RecentTransactions />
    </div>
  );
}
```

### 6.2 Dashboard Widget Components

**Create these components in** `apps/web/src/components/dashboard/`:

- `NetWorthCard.tsx` - Shows net worth with mini chart
- `CashFlowCard.tsx` - Income vs expenses this month
- `BudgetOverview.tsx` - Budget progress summary
- `InsightCards.tsx` - AI insight cards carousel
- `UpcomingBills.tsx` - Next 5 bills due
- `RecentTransactions.tsx` - Last 10 transactions

Each should:
- Use proper loading states (skeletons)
- Handle empty states
- Be responsive
- Support dark mode
- Have proper accessibility

---

## PHASE 7: VALIDATION & TESTING

### 7.1 Manual Testing Checklist

```markdown
## Mobile Testing
- [ ] Hamburger menu works
- [ ] Drawer slides smoothly
- [ ] Bottom nav works
- [ ] All pages scroll properly
- [ ] No horizontal overflow
- [ ] Touch targets are 44px+

## Dark Mode Testing
- [ ] System preference detected
- [ ] Toggle works
- [ ] All pages look good
- [ ] Charts adapt colors
- [ ] No white flashes

## Accessibility Testing
- [ ] Tab through entire app
- [ ] Skip link works
- [ ] Screen reader test
- [ ] Color contrast check
- [ ] Focus visible everywhere

## Chart Testing
- [ ] Spending chart renders
- [ ] Category pie chart renders
- [ ] Budget progress bars work
- [ ] Net worth chart renders
- [ ] Tooltips work
- [ ] Responsive sizing

## Polish Testing
- [ ] Loading skeletons show
- [ ] Toast notifications work
- [ ] Empty states display
- [ ] Command palette (⌘K) works
- [ ] Animations are smooth
```

### 7.2 Lighthouse Audit

```bash
npx lighthouse http://localhost:3000 --view
```

**Targets:**
- Performance: >90
- Accessibility: >95
- Best Practices: >95
- SEO: >90

### 7.3 Bundle Size Check

```bash
cd apps/web
npm run build
```

**Target**: Total JS < 250KB gzipped

---

## EXECUTION ORDER

```
Day 1:
├── Phase 1: Mobile Navigation (4 hours)
└── Phase 2: Charts - Start (2 hours)

Day 2:
├── Phase 2: Charts - Complete (2 hours)
├── Phase 3: Dark Mode (3 hours)
└── Phase 4: Accessibility - Start (2 hours)

Day 3:
├── Phase 4: Accessibility - Complete (2 hours)
└── Phase 5: UI Polish (4 hours)

Day 4:
├── Phase 6: Dashboard Redesign (6 hours)

Day 5:
├── Phase 6: Dashboard - Complete (2 hours)
└── Phase 7: Testing & Fixes (4 hours)
```

---

## SUCCESS CRITERIA

| Metric | Before | Target | After |
|--------|--------|--------|-------|
| Overall Score | 6.1/10 | 8.5/10 | ___ |
| UX/UI Score | 6.7/10 | 9.0/10 | ___ |
| 2025 Standards | 5.4/10 | 8.5/10 | ___ |
| Mobile Navigation | ❌ | ✅ | ___ |
| Charts | ❌ | ✅ | ___ |
| Dark Mode | ❌ | ✅ | ___ |
| Accessibility | ❌ | ✅ | ___ |
| Lighthouse Perf | ___ | >90 | ___ |
| Lighthouse A11y | ___ | >95 | ___ |

---

*Build it beautiful. Build it accessible. Build it for 2025.*
