# Phase 2: Frontend Fixes

## Your Role
You are a senior React/Next.js developer. Fix all frontend issues to make this production-ready.

## Context
- App: LedgerLoop (personal finance)
- Frontend: `apps/web/src/`
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- Auth: DISABLED - remove all auth UI/logic

## Critical Fixes Required

### 1. Remove Authentication UI

Since auth is disabled, remove/bypass all auth-related UI:

**Files to modify:**
- `app/login/page.tsx` - Delete or redirect to `/`
- `middleware.ts` - Remove auth redirects
- `contexts/AuthContext.tsx` - Make it a no-op or remove
- `components/auth/*` - Archive or delete

**Search for auth references:**
```bash
grep -rn "isAuthenticated\|useAuth\|login\|logout\|ProtectedRoute" apps/web/src/
```

**Replace with:**
```tsx
// If AuthContext is used, make it always "authenticated"
export const useAuth = () => ({
  isAuthenticated: true,
  user: { id: 'local-user', name: 'User' },
  login: async () => {},
  logout: async () => {},
});
```

### 2. Fix/Remove Placeholder Components

Find and fix all placeholders:

```bash
grep -rn "placeholder\|TODO\|FIXME\|Coming Soon\|Not Implemented" apps/web/src/
```

For each placeholder:
- If feature exists in backend → implement the UI
- If feature doesn't exist → remove the UI element entirely
- If it's a "coming soon" page → either implement or remove from navigation

### 3. Fix Broken Navigation Links

Check ALL navigation links work:

**Sidebar/Nav items** (check `components/layout/Sidebar.tsx` or similar):
```
/                    → Dashboard
/transactions        → Transactions list
/categories          → Categories management
/rules               → Rules management
/recurring           → Recurring transactions
/transfers           → Transfer pairs
/ai                  → AI features
/analytics           → Analytics (if exists)
/ingest              → Import data
/export              → Export data
/settings            → Settings
/audit               → Audit log
```

For each route:
1. Verify page exists at `app/[route]/page.tsx`
2. Verify page renders without errors
3. Verify page has content (not empty/placeholder)

### 4. Remove Dead Pages

Check for orphaned pages with no navigation:
```bash
ls -la apps/web/src/app/*/
```

If a page exists but:
- No link in navigation
- No purpose
- Is a placeholder

→ Delete it or add proper navigation

### 5. Clean Up Console Statements

Remove all console.log in production code:

```bash
grep -rn "console\." apps/web/src/
```

Replace with:
- Error handling → proper error boundary
- Debug logs → remove entirely
- Important logs → use a proper logger or keep only in development:

```tsx
// Only log in development
if (process.env.NODE_ENV === 'development') {
  console.log('Debug:', data);
}
```

### 6. Fix TypeScript Errors

Run TypeScript check and fix ALL errors:
```bash
cd apps/web
npx tsc --noEmit
```

Common fixes:
- Add proper types to function parameters
- Fix `any` types where possible
- Add null checks

### 7. Remove Unused Dependencies/Imports

Check each file for unused imports:
```bash
# This will show warnings during build
cd apps/web
npm run build
```

### 8. Fix API URL Configuration

Ensure API URLs are configurable:

```tsx
// utils/api.ts or similar
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### 9. Error Boundaries

Add error boundaries for each major section:

```tsx
// components/ErrorBoundary.tsx
'use client';
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 bg-red-50 text-red-700 rounded">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### 10. Loading States

Ensure all data-fetching pages have proper loading states:

```tsx
// Each page with data should have:
if (loading) {
  return <LoadingSpinner />;
}

if (error) {
  return <ErrorDisplay error={error} />;
}

if (!data || data.length === 0) {
  return <EmptyState message="No data found" />;
}
```

## Execution Steps

1. **Audit current state:**
   ```bash
   ls -la apps/web/src/app/
   ls -la apps/web/src/components/
   ```

2. **Remove auth UI** (login page, protected routes)

3. **Fix/remove placeholders**

4. **Verify all routes render**

5. **Run build to check for errors:**
   ```bash
   cd apps/web
   npm run build
   ```

6. **Fix any build errors**

## Output Required

Create `FRONTEND_FIXES_LOG.md` documenting:
- Pages removed
- Pages fixed
- Components modified
- Any backend API gaps discovered

## Rules
- DO NOT change API endpoint URLs (must match backend)
- DO NOT add new features - only fix existing
- DO ensure the app builds successfully
- DO test each page renders in browser
