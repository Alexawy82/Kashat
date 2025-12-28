# Contributing to Kashat

Thank you for your interest in contributing to Kashat!

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) OpenAI API key for AI features

### Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment
export PYTHONPATH=apps/backend/src
export KASHAT_DATA_DIR=./data

# Run API server
uvicorn kashat.api.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd apps/web
npm install
export NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000/api"
npm run dev
```

## Running Tests

### Backend Tests

```bash
# Run all tests
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests -v

# Run specific test file
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests/test_networth.py -v

# Run with coverage (requires pytest-cov)
PYTHONPATH=apps/backend/src python -m pytest apps/backend/tests --cov=kashat --cov-report=html
```

### Frontend Build Check

```bash
cd apps/web
npm run build
```

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, use type hints for all public functions
- **TypeScript**: Use strict mode, prefer interfaces over type aliases
- **SQL**: Use `[transaction]` instead of `transaction` (reserved word in SQLite)

### Database Conventions

- Use SQLite-compatible SQL syntax
- Add migrations for schema changes in `apps/backend/db/migrations/`
- Migration files should be numbered: `0008_feature_name.sql`
- Always use `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS`

### API Conventions

- All endpoints should return JSON
- Use consistent error responses via `kashat/api/errors.py`
- Add Pydantic models for request/response validation
- Document endpoints with docstrings

### Testing Requirements

- Add tests for all new features
- Tests should use `_setup_client()` pattern for isolation
- Use `LEDGERLOOP_DATA_DIR` or `KASHAT_DATA_DIR` for test isolation
- Aim for 70%+ code coverage

## Project Structure

```
apps/
├── backend/
│   ├── src/kashat/          # Main package
│   │   ├── api/             # FastAPI routes
│   │   │   └── routes/      # Route modules
│   │   ├── ai/              # AI modules
│   │   ├── detect/          # Detection algorithms
│   │   └── parse/           # Statement parsers
│   ├── db/
│   │   └── migrations/      # SQL migrations
│   └── tests/               # Test suite
└── web/
    └── src/
        ├── app/             # Next.js pages
        ├── components/      # React components
        ├── hooks/           # React Query hooks
        └── lib/             # Utilities
```

## Adding New Features

### Backend Feature

1. Create route file in `apps/backend/src/kashat/api/routes/`
2. Add Pydantic models for requests/responses
3. Register router in `apps/backend/src/kashat/api/__init__.py`
4. Add migration if schema changes needed
5. Write tests in `apps/backend/tests/`

### Frontend Feature

1. Create page in `apps/web/src/app/`
2. Add API hooks in `apps/web/src/hooks/`
3. Create components in `apps/web/src/components/`
4. Update navigation in `apps/web/src/components/layout/Sidebar.tsx`

## Commit Guidelines

- Use clear, descriptive commit messages
- Reference issue numbers when applicable
- Keep commits focused on single changes

Example:
```
feat(budget): add budget progress endpoint

- Added GET /api/budgets/{id}/progress endpoint
- Returns current period spending vs limits
- Added tests for budget progress calculation
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests locally
5. Submit PR with clear description

## Privacy First

Kashat is a local-first, privacy-focused application:
- All data stays on the user's machine
- No telemetry or external data collection
- No cloud sync by design

## Questions?

Open an issue for questions or suggestions.
