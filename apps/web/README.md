Web App (Next.js)

Placeholder for V1 UI. Intended stack:
- Next.js 14, React 18
- UI talks to local FastAPI at `http://localhost:8000/api`

Suggested bootstrap (when ready):
1. `pnpm create next-app apps/web --ts --eslint --tailwind --app --src-dir`
2. Add `.env.local` with `NEXT_PUBLIC_API_BASE=http://localhost:8000/api`
3. Implement pages for Transactions, Rules, Transfers, Recurring, Dashboard.

For now, use the backend endpoints directly via HTTP clients (curl, Insomnia) to validate flows.
