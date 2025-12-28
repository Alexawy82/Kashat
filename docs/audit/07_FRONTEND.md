# Frontend Documentation

## Overview

The LedgerLoop frontend is a **Next.js 14.2** application using the App Router pattern with React 18, TypeScript 5.9, and TanStack Query for server state management.

---

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js | 14.2.35 |
| UI Library | React | 18.2.0 |
| Language | TypeScript | 5.9.3 |
| State Management | TanStack Query | 5.90.12 |
| Styling | Tailwind CSS | 3.4.17 |
| Components | shadcn/ui (Radix) | Various |
| Tables | TanStack Table | 8.21.3 |
| Charts | Recharts | 3.2.1 |
| Icons | Lucide React | 0.544.0 |

---

## Page Inventory

### Main Pages

| Route | File | Purpose |
|-------|------|---------|
| `/` | app/page.tsx | Dashboard with AI insights |
| `/analytics` | app/analytics/page.tsx | Financial analytics |
| `/transactions` | app/transactions/page.tsx | Transaction list |
| `/categories` | app/categories/page.tsx | Category management |
| `/import` | app/import/page.tsx | File import |
| `/recurring` | app/recurring/page.tsx | Subscriptions & bills |
| `/transfers` | app/transfers/page.tsx | Transfer detection |
| `/rules` | app/rules/page.tsx | Automation rules |
| `/pulse` | app/pulse/page.tsx | System health |

### Settings Pages

| Route | File | Purpose |
|-------|------|---------|
| `/settings` | app/settings/page.tsx | Settings overview |
| `/settings/automation` | app/settings/automation/page.tsx | Rules config |
| `/settings/categories` | app/settings/categories/page.tsx | Category setup |
| `/settings/system` | app/settings/system/page.tsx | AI & system config |

---

## Component Inventory

### Dashboard Components

| Component | File | Purpose |
|-----------|------|---------|
| HealthScoreCard | dashboard/HealthScoreCard.tsx | Financial health display |
| RunwayCard | dashboard/RunwayCard.tsx | Cash runway projection |
| IntelligenceFeed | dashboard/IntelligenceFeed.tsx | AI insights feed |
| SpendingBehaviorCard | dashboard/SpendingBehaviorCard.tsx | Spending patterns |
| CashflowSummaryCard | dashboard/CashflowSummaryCard.tsx | Cashflow visualization |
| AnomalyAlerts | dashboard/AnomalyAlerts.tsx | Anomaly alerts |
| RecurringSummaryWidget | dashboard/RecurringSummaryWidget.tsx | Recurring summary |

### Layout Components

| Component | File | Purpose |
|-----------|------|---------|
| Sidebar | layout/Sidebar.tsx | Navigation sidebar |
| CommandPalette | layout/CommandPalette.tsx | Cmd+K search |

### Transaction Components

| Component | File | Purpose |
|-----------|------|---------|
| data-table | transactions/data-table.tsx | Main transaction table |
| columns | transactions/columns.tsx | Column definitions |
| TransactionActions | transactions/TransactionActions.tsx | Row actions |

### Recurring Components

| Component | File | Purpose |
|-----------|------|---------|
| SummaryBar | recurring/components/SummaryBar.tsx | Summary stats |
| SeriesCard | recurring/components/SeriesCard.tsx | Series card |
| SeriesDetailSheet | recurring/components/SeriesDetailSheet.tsx | Detail sheet |
| ReportsModal | recurring/components/ReportsModal.tsx | Reports modal |
| AlertsBanner | recurring/components/AlertsBanner.tsx | Alerts |
| InsightsPanel | recurring/components/InsightsPanel.tsx | Insights |
| UpcomingWidget | recurring/components/UpcomingWidget.tsx | Upcoming |
| CategoryOverview | recurring/components/CategoryOverview.tsx | By category |
| TypeTabs | recurring/components/TypeTabs.tsx | Type tabs |
| TypeSection | recurring/components/TypeSection.tsx | Type section |

### Transfer Components

| Component | File | Purpose |
|-----------|------|---------|
| StatsCards | transfers/components/StatsCards.tsx | P2P stats |
| CounterpartyCard | transfers/components/CounterpartyCard.tsx | Counterparty |
| CounterpartySheet | transfers/components/CounterpartySheet.tsx | Detail sheet |
| CounterpartyFilters | transfers/components/CounterpartyFilters.tsx | Filters |
| MergeDialog | transfers/components/MergeDialog.tsx | Merge dialog |
| TransfersTab | transfers/components/TransfersTab.tsx | Tab view |
| DetectionButtons | transfers/components/DetectionButtons.tsx | Actions |

### UI Components (shadcn/ui)

| Component | File | Purpose |
|-----------|------|---------|
| Button | ui/button.tsx | Button variants |
| Card | ui/card.tsx | Card container |
| Input | ui/input.tsx | Text input |
| Table | ui/table.tsx | Table primitive |
| Sheet | ui/sheet.tsx | Side panel |
| Dialog | ui/dialog.tsx | Modal dialog |
| Command | ui/command.tsx | Command palette |
| Badge | ui/badge.tsx | Labels |
| Tabs | ui/tabs.tsx | Tab component |
| Label | ui/label.tsx | Form label |
| Alert | ui/alert.tsx | Alert box |
| DropdownMenu | ui/dropdown-menu.tsx | Dropdown |
| Slider | ui/slider.tsx | Range slider |
| Switch | ui/switch.tsx | Toggle |
| Select | ui/select.tsx | Select dropdown |
| Checkbox | ui/checkbox.tsx | Checkbox |
| Separator | ui/separator.tsx | Separator |
| Progress | ui/progress.tsx | Progress bar |

---

## Custom Hooks

### Data Fetching Hooks

| Hook | File | API Calls |
|------|------|-----------|
| useAccounts | useAccounts.ts | GET /accounts |
| useTransactions | useTransactions.ts | GET /transactions, PATCH, DELETE |
| useCategories | useCategories.ts | GET /categories, POST, AI suggestions |
| useAnalytics | useAnalytics.ts | GET /analytics/* |
| useRecurring | useRecurring.ts | GET /recurring, confirm, reject |
| useP2P | useP2P.ts | GET /p2p/*, detection |
| useImports | useImports.ts | POST /imports/*, runs |
| useIntelligence | useIntelligence.ts | GET /intelligence/* |
| useSettings | useSettings.ts | GET/POST /settings |
| useAIQueue | useAIQueue.ts | GET /ai/queue/*, bulk jobs |
| useAutomation | useAutomation.ts | Rules CRUD |
| usePulse | usePulse.ts | System health |

### Utility Hooks

| Hook | File | Purpose |
|------|------|---------|
| useDebounce | useDebounce.ts | Input debouncing |

### Hook Pattern

All hooks follow the TanStack Query pattern:

```typescript
export function useTransactions(filter: TransactionFilter) {
  return useQuery({
    queryKey: ['transactions', filter],
    queryFn: async () => {
      const { data, error } = await client.get('/api/transactions', {
        params: filter
      });
      if (error) throw new Error(error.message);
      return data;
    },
    staleTime: 60_000, // 1 minute
  });
}
```

---

## API Client

### Configuration

```typescript
// lib/api-client.ts
const client = {
  get: async (path, options) => fetch(path, { method: 'GET', ...options }),
  post: async (path, body, options) => fetch(path, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
    ...options
  }),
  // ... put, patch, delete
};
```

### OpenAPI Generated Client

Generated from `openapi.json` (235KB) using `@hey-api/openapi-ts`:

```typescript
// openapi-ts.config.ts
export default defineConfig({
  client: '@hey-api/client-fetch',
  input: 'openapi.json',
  output: 'src/lib/api',
});
```

### Environment Variables

```bash
NEXT_PUBLIC_API_BASE=/api  # API proxy path
NEXT_PUBLIC_WS_TOKEN=...   # WebSocket auth (optional)
NEXT_PUBLIC_ENABLE_REALTIME=0  # Real-time features
```

---

## State Management

### Primary: TanStack Query

- All server state via `useQuery()` and `useMutation()`
- Automatic caching with 60-second stale time
- Query invalidation on mutations
- Optimistic updates where appropriate

### Query Client Configuration

```typescript
// components/providers.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});
```

### No Zustand Usage

Despite being installed, Zustand is not currently used. All state flows through TanStack Query.

---

## Styling

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // CSS variable-based colors for light/dark
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: 'hsl(var(--primary))',
        // ... more semantic colors
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### Component Styling

- Tailwind utility classes throughout
- shadcn/ui components with variants
- `cn()` utility for conditional classes

```typescript
// lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

## Routing

### Next.js App Router

```
app/
├── layout.tsx          # Root layout with Sidebar
├── page.tsx            # Dashboard (/)
├── analytics/
│   └── page.tsx        # /analytics
├── transactions/
│   ├── page.tsx        # /transactions
│   ├── columns.tsx     # Column definitions
│   └── data-table.tsx  # Table component
├── settings/
│   ├── layout.tsx      # Settings sub-layout
│   ├── page.tsx        # /settings
│   ├── automation/
│   │   └── page.tsx    # /settings/automation
│   └── ...
└── ...
```

### Route Redirects

```javascript
// next.config.js
async redirects() {
  return [
    { source: '/analyze', destination: '/ai', permanent: true },
    { source: '/analytics', destination: '/', permanent: true },
    { source: '/categories', destination: '/settings/categories', permanent: true },
    { source: '/rules', destination: '/settings/automation', permanent: true },
    { source: '/pulse', destination: '/settings/system', permanent: true },
  ];
}
```

### API Proxy

```javascript
// next.config.js
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: `${backendOrigin}/api/:path*`,
    },
  ];
}
```

---

## Type Definitions

### Domain Types

```typescript
// types/domain.ts
interface Transaction {
  id: string;
  account_id: string;
  posted_at: string;
  amount: number;
  description_norm: string;
  category_id?: string;
  category_name?: string;
  is_business: boolean;
  is_income: boolean;
  is_adjustment: boolean;
  ai_merchant_name?: string;
  ai_confidence_score?: number;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

interface TransactionFilter {
  account_id?: string;
  start_date?: string;
  end_date?: string;
  category_id?: string;
  uncategorized?: boolean;
  include_transfers?: boolean;
}
```

### Generated Types

500+ types auto-generated from OpenAPI spec in `lib/api/types.gen.ts`.

---

## Testing

### E2E Tests (Playwright)

```typescript
// e2e/flows.spec.ts
test('Recurring: suggest -> approve -> confirmed shows', async ({ page }) => {
  // Test recurring workflow
});

test('Transfers: suggest -> approve -> toggle include', async ({ page }) => {
  // Test transfer workflow
});

test('Data Management: upload -> list -> summary -> delete', async ({ page }) => {
  // Test import lifecycle
});
```

### Playwright Configuration

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: process.env.NEXT_PUBLIC_API_BASE || 'http://127.0.0.1:8000/api',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

---

## Build Configuration

### Next.js Config

```javascript
// next.config.js
module.exports = {
  output: 'standalone',  // For Docker
  distDir: process.env.NODE_ENV === 'production' ? '.next' : '/tmp/ll_next',
  // ... rewrites, redirects
};
```

### TypeScript Config

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "esnext",
    "moduleResolution": "bundler",
    "strict": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

---

## Key Patterns

### 1. Hook-Based Data Fetching

All data flows through custom hooks using TanStack Query.

### 2. Query Key Hierarchy

```typescript
['transactions', filter]           // Transaction list
['transactions', id]               // Single transaction
['categories']                     // All categories
['recurring', 'summary']           // Recurring summary
['analytics', 'dashboard', params] // Dashboard data
```

### 3. Mutation with Invalidation

```typescript
const assignCategory = useMutation({
  mutationFn: (data) => client.post(`/api/transactions/${data.txId}/category`, data),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['transactions'] });
    queryClient.invalidateQueries({ queryKey: ['categories'] });
  },
});
```

### 4. Component Composition

Pages compose feature components which compose UI primitives.

### 5. Progressive Disclosure

Settings organized under `/settings/*` routes for cleaner navigation.

---

*Generated by Claude Code Audit - December 27, 2025*
