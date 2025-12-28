# Testing Documentation

## Overview

LedgerLoop has a comprehensive test suite with **38 backend test files** and **1 e2e test file** covering API endpoints, business logic, AI features, and user workflows.

---

## Test Statistics

| Metric | Value |
|--------|-------|
| Backend Test Files | 38 |
| E2E Test Files | 1 |
| Total Test Functions | 100+ |
| Coverage Threshold | 45% minimum |
| Test Framework | pytest |
| E2E Framework | Playwright |

---

## Test Categories

### API Tests (6 files)

| File | Tests | Focus |
|------|-------|-------|
| test_api_auth.py | 2 | Authentication, JWT, authorization |
| test_api_errors.py | 6 | Error handling, exception responses |
| test_api_smoke.py | 5 | Basic endpoint smoke tests |
| test_contract_routes.py | 1 | Route existence validation |
| test_route_integrity.py | 3 | Route registration, no duplicates |
| test_frontend_api_contract.py | 1 | Frontend-backend API contract |

### Analytics Tests (5 files)

| File | Tests | Focus |
|------|-------|-------|
| test_analytics_adjustments_consistency.py | 1 | Adjustment exclusion |
| test_analytics_dashboard.py | 1 | Dashboard endpoint |
| test_analytics_reconcile.py | 1 | PDF reconciliation |
| test_endpoints_analytics_export.py | 3 | Analytics and export |

### AI/ML Tests (3 files)

| File | Tests | Focus |
|------|-------|-------|
| test_ai_categories_acceptance.py | 3 | AI category acceptance |
| test_merchant_memory.py | 9+ | Merchant learning system |
| test_merchant_memory_api.py | 15+ | Merchant memory API |

### Import Tests (5 files)

| File | Tests | Focus |
|------|-------|-------|
| test_boa_goldens.py | 1 | BoA PDF parsing accuracy |
| test_ingest_golden.py | 3 | CSV row normalization |
| test_imports_parse_route.py | 2 | Import parsing route |
| test_import_runs_console.py | 1 | Import run management |
| test_pdf_importer.py | 1 | PDF import (placeholder) |

### Detection Tests (6 files)

| File | Tests | Focus |
|------|-------|-------|
| test_detect_p2p.py | 4 | P2P payment detection |
| test_detect_zelle.py | 1 | Zelle detection |
| test_income_adjustments.py | 2 | Income/adjustment detection |
| test_audit_filters.py | 4 | Audit log filtering |

### Core Logic Tests (8 files)

| File | Tests | Focus |
|------|-------|-------|
| test_dedup.py | 1 | Fingerprint deduplication |
| test_normalization.py | 4 | Data normalization |
| test_rules.py | 4 | Rule engine |
| test_recurring.py | 8 | Recurring detection |
| test_transfers.py | 2 | Transfer matching |
| test_transfers_v2.py | 1 | Online banking parsing |
| test_transfers_v2_eval.py | 1 | Transfer precision/recall |
| test_transfers_v2_labels.py | 1 | Transfer labels |

### Integration Tests (4 files)

| File | Tests | Focus |
|------|-------|-------|
| test_bulk_import_and_runs.py | 1 | Bulk import workflow |
| test_reimport_integration.py | 1 | Re-import idempotency |
| test_categories_crud.py | 1 | Category operations |
| test_workflows_routes.py | 3 | Workflow CRUD |

### Schema & Security (3 files)

| File | Tests | Focus |
|------|-------|-------|
| test_schema_versioning.py | 1 | Schema version table |
| test_security.py | 1 | Data redaction |
| test_ops_metrics.py | 1 | Operational metrics |

---

## Test Fixtures

### conftest.py

```python
# Session-scoped fixtures
@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Temporary directory for test database."""
    return tmp_path_factory.mktemp("data")

@pytest.fixture(scope="session")
def test_app(test_data_dir):
    """FastAPI application instance."""
    os.environ["LEDGERLOOP_DATA_DIR"] = str(test_data_dir)
    from ledgerloop.api import create_app
    return create_app()

@pytest.fixture(scope="session")
def client(test_app):
    """Test client for API calls."""
    return TestClient(test_app)

@pytest.fixture(scope="session")
def auth_token(client):
    """Admin authentication token."""
    response = client.post("/api/auth/login", json={...})
    return response.json()["access_token"]

@pytest.fixture(scope="session")
def auth_headers(auth_token):
    """Authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}

# Function-scoped fixtures
@pytest.fixture
def db_conn(test_data_dir):
    """Isolated database connection per test."""
    conn = connect(test_data_dir / "test.db")
    yield conn
    conn.close()

@pytest.fixture
def sample_transactions():
    """Pre-built transaction data."""
    return [
        {"description": "AMAZON MKTPLC", "amount": -50.00, ...},
        {"description": "PAYROLL DEPOSIT", "amount": 2000.00, ...},
    ]

@pytest.fixture
def seed_transactions(db_conn, sample_transactions):
    """Helper to insert test transactions."""
    def _seed(transactions=None):
        txs = transactions or sample_transactions
        for tx in txs:
            # Insert into database
            ...
    return _seed
```

---

## Example Tests

### API Smoke Test

```python
# test_api_smoke.py
class TestAPISmoke(unittest.TestCase):
    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", response.json())

    def test_import_csv_and_list_transactions(self):
        # Upload CSV
        with open("fixture.csv", "rb") as f:
            response = self.client.post("/api/imports/csv", files={"file": f})
        self.assertEqual(response.status_code, 200)

        # List transactions
        response = self.client.get("/api/transactions")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()["items"]), 0)
```

### Recurring Detection Test

```python
# test_recurring.py
def test_detect_candidates(db_conn, seed_transactions):
    # Seed monthly Netflix charges
    seed_transactions([
        {"description": "NETFLIX", "amount": -15.99, "posted_at": "2024-01-15"},
        {"description": "NETFLIX", "amount": -15.99, "posted_at": "2024-02-15"},
        {"description": "NETFLIX", "amount": -15.99, "posted_at": "2024-03-15"},
    ])

    # Detect recurring
    candidates = detect_recurring_candidates(db_conn)

    # Verify detection
    assert len(candidates) == 1
    assert candidates[0]["name"] == "NETFLIX"
    assert candidates[0]["cadence"] == "monthly"
```

### Merchant Memory Test

```python
# test_merchant_memory.py
class TestMerchantLearning:
    def test_learn_from_categorization(self, db_conn):
        # Categorize a transaction
        learn_merchant_category(
            db_conn,
            merchant_pattern="STARBUCKS",
            category_id="food_dining"
        )

        # Verify learning
        prediction = predict_category(db_conn, "STARBUCKS STORE 123")
        assert prediction["category_id"] == "food_dining"
        assert prediction["confidence"] > 0.9
```

### Transfer Detection Test

```python
# test_transfers.py
def test_transfer_helpers_and_flow(db_conn, seed_transactions):
    # Create matching transfers
    seed_transactions([
        {"description": "TRANSFER TO SAVINGS", "amount": -1000, "account_id": "checking"},
        {"description": "TRANSFER FROM CHECKING", "amount": 1000, "account_id": "savings"},
    ])

    # Suggest transfers
    suggestions = suggest_transfers(db_conn)
    assert len(suggestions) == 1

    # Confirm transfer
    confirm_transfer(db_conn, suggestions[0]["left_id"], suggestions[0]["right_id"])

    # Verify confirmation
    transfers = list_transfers(db_conn, status="confirmed")
    assert len(transfers) == 1
```

---

## E2E Tests

### flows.spec.ts

```typescript
import { test, expect } from '@playwright/test';

test('Recurring: suggest -> approve -> confirmed shows', async ({ page, request }) => {
  // Seed test data
  await request.post('/api/recurring/suggest');

  // Navigate to recurring page
  await page.goto('/recurring');

  // Find pending series
  const pendingCard = page.locator('[data-status="pending"]').first();
  await expect(pendingCard).toBeVisible();

  // Confirm series
  await pendingCard.locator('button:has-text("Confirm")').click();

  // Verify confirmed
  await expect(page.locator('[data-status="confirmed"]')).toHaveCount(1);
});

test('Transfers: suggest -> approve -> toggle include', async ({ page, request }) => {
  // Run transfer detection
  await request.post('/api/transfers/suggest_v3');

  // Navigate to transfers
  await page.goto('/transfers');

  // Confirm a transfer
  await page.locator('.transfer-pair').first().locator('button:has-text("Confirm")').click();

  // Toggle analytics inclusion
  await page.locator('button:has-text("Include in Analytics")').click();

  // Verify toggle
  await expect(page.locator('.analytics-included')).toBeVisible();
});

test('Data Management: upload -> list -> summary -> delete', async ({ page }) => {
  // Upload CSV
  await page.goto('/import');
  await page.setInputFiles('input[type="file"]', 'fixtures/test.csv');
  await page.locator('button:has-text("Upload")').click();

  // Wait for import
  await expect(page.locator('text=Import complete')).toBeVisible();

  // View summary
  await page.locator('button:has-text("View Summary")').click();
  await expect(page.locator('.import-summary')).toBeVisible();

  // Delete import
  await page.locator('button:has-text("Delete")').click();
  await page.locator('button:has-text("Confirm Delete")').click();

  // Verify deletion
  await expect(page.locator('.import-run')).toHaveCount(0);
});
```

---

## Coverage Configuration

### Included Modules

- `ledgerloop.api` - All API routes
- `ledgerloop.db` - Database layer
- `ledgerloop.transfers` - Transfer detection
- `ledgerloop.recurring` - Recurring detection

### Excluded Modules

- `ai_*.py` - AI modules (too dependent on external services)
- `analytics/*.py` - Analytics (covered by integration tests)
- `ingest_pdf.py` - PDF import (requires pdfplumber)
- `parse/*.py` - Bank parsers (require fixtures)
- `cli.py` - CLI (tested manually)

---

## Running Tests

### All Tests

```bash
make test
# or
pytest -q
```

### Specific Test File

```bash
pytest apps/backend/tests/test_recurring.py -v
```

### With Coverage Report

```bash
pytest --cov=ledgerloop --cov-report=html
```

### E2E Tests

```bash
cd apps/web
npm run test:e2e
# or
npx playwright test
```

---

## Test Data Fixtures

### CSV Fixtures

Located in `apps/backend/tests/fixtures/`:

- `sample_bank.csv` - Standard bank format
- `sample_boa.csv` - Bank of America format
- `sample_multi_account.csv` - Multiple accounts

### PDF Fixtures

Located in `bank/`:

- Bank of America statement PDFs for golden file testing

### Golden Files

Located in `apps/backend/tests/goldens/`:

- Expected parsing outputs for comparison

---

## CI/CD Integration

Tests should run on every PR with:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest --cov --cov-report=xml
      - uses: codecov/codecov-action@v4
```

---

*Generated by Claude Code Audit - December 27, 2025*
