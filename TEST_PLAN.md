# LedgerLoop Test Plan

## Quick Verification Steps

### 1. Application Startup (5 minutes)

```bash
# Start the application
./setup          # First time only
./start          # Start both backend and frontend

# Verify services
./scripts/verify-app.sh
```

**Expected Results**:
- ✅ Backend API running on http://localhost:8000
- ✅ Frontend web running on http://localhost:3000
- ✅ Database connectivity confirmed
- ✅ All API endpoints responding

### 2. Basic Functionality Test (10 minutes)

#### Web Interface Test
1. **Dashboard Access**: Visit http://localhost:3000
   - Should show empty or sample dashboard
   - Navigation menu should be functional

2. **File Upload**: Visit http://localhost:3000/ingest
   - Upload a CSV file from `data/fixtures/`
   - Upload a PDF file from `bank/` directory
   - Verify parsing results and balance validation

3. **Transaction View**: Visit http://localhost:3000/transactions
   - Browse imported transactions
   - Test filtering and search
   - Try bulk operations

4. **Analytics**: Visit http://localhost:3000/analytics
   - Check charts and summaries
   - Verify date range filtering

#### API Test
```bash
# Health check
curl http://localhost:8000/api/health

# List transactions
curl http://localhost:8000/api/transactions?limit=10

# Get categories
curl http://localhost:8000/api/categories

# Analytics summary
curl http://localhost:8000/api/analytics/summary

# Predictions
curl http://localhost:8000/api/analytics/predictions

# CSV export (new)
curl -I "http://localhost:8000/api/export/csv?from=2024-01-01&to=2024-12-31"
```

### 3. CLI Interface Test (5 minutes)

```bash
# Set up CLI
cd /mnt/c/Users/Marwan/OneDrive/Desktop/AI/Flos
export PYTHONPATH=apps/backend/src

# Test CLI commands
python -m ledgerloop.cli --help
python -m ledgerloop.cli stats
python -m ledgerloop.cli health

# Test file import (if sample file exists)
python -m ledgerloop.cli ingest data/fixtures/sample_bank.csv
```

### 4. Advanced Features Test (10 minutes)

#### AI Processing
1. Enable AI in settings
2. Upload transactions
3. Verify AI categorization
4. Check confidence scores

#### Transfer Detection
```bash
python -m ledgerloop.cli detect transfers
```

#### Recurring Detection
```bash
python -m ledgerloop.cli detect recurring
```

#### Rules Engine
1. Create a rule via web interface
2. Test rule preview
3. Apply rules to transactions

### 5. Data Export Test (5 minutes)

#### Web Export
1. Visit http://localhost:3000/export
2. Export transactions as CSV
3. Verify file content

#### CLI Export
```bash
python -m ledgerloop.cli export csv -o test_export.csv
python -m ledgerloop.cli export json -o test_export.json
```

## Test Data

### Sample CSV Format
```csv
Date,Description,Amount,Balance
2024-01-01,GROCERY STORE,-45.67,1234.56
2024-01-02,SALARY DEPOSIT,2500.00,3734.56
2024-01-03,TRANSFER TO SAVINGS,-500.00,3234.56
```

### Sample PDF
- Use any Bank of America PDF statement
- Place in `bank/` directory
- Test parsing and validation

## Golden Dataset Tests

### Automated Tests
```bash
# Run existing test suite
cd apps/backend
export PYTHONPATH=src
python -m pytest tests/ -v

# Specific tests
python -m pytest tests/test_boa_goldens.py -v
python -m pytest tests/test_dedup.py -v
python -m pytest tests/test_transfers.py -v
python -m pytest tests/test_endpoints_analytics_export.py -v
```

### Manual Golden Tests
1. Use PDFs in `bank/` directory
2. Compare against CSV files in `data/fixtures/boa_goldens/`
3. Verify transaction counts match
4. Verify balance calculations

## Performance Tests

### Large File Import
1. Create or obtain large CSV file (1000+ transactions)
2. Time the import process
3. Verify memory usage
4. Check database performance

### Concurrent Operations
1. Start multiple import operations
2. Run AI processing while importing
3. Verify system stability

## Security Tests

### Authentication
1. Test API endpoints with/without tokens
2. Verify CORS configuration
3. Check for sensitive data in logs

### Data Privacy
1. Verify no PII in logs
2. Test local AI processing
3. Confirm data stays local

## Browser Compatibility

### Desktop
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

### Mobile
- iOS Safari
- Android Chrome
- Responsive design verification

## Error Handling Tests

### Invalid File Formats
1. Upload non-CSV/PDF files
2. Upload corrupted files
3. Verify error messages

### Network Issues
1. Stop backend during frontend operation
2. Test offline behavior
3. Verify error recovery

### Database Issues
1. Database permission errors
2. Disk space issues
3. Connection failures

## Expected Test Results

### Minimum Acceptance Criteria
- [ ] Application starts successfully
- [ ] Can import CSV and PDF files
- [ ] Transactions are parsed correctly
- [ ] Balance validation passes for golden datasets
- [ ] Web interface is fully functional
- [ ] API endpoints respond correctly
- [ ] CLI interface works for basic operations
- [ ] Export functionality works
- [ ] No sensitive data in logs
- [ ] Error handling is graceful

### Performance Benchmarks
- [ ] Import 1000 transactions in < 30 seconds
- [ ] Web pages load in < 3 seconds
- [ ] API responses in < 500ms for standard queries
- [ ] Memory usage < 500MB for normal operations

### Feature Completeness
- [ ] All major workflows function end-to-end
- [ ] AI processing works (if configured)
- [ ] Transfer detection finds obvious pairs
- [ ] Recurring detection identifies patterns
- [ ] Rules engine applies correctly
- [ ] Analytics provide meaningful insights

## Troubleshooting

### Common Issues

**Port conflicts**:
```bash
./start status     # Check what's running
./start stop both  # Stop services
./start            # Restart with auto port detection
```

**Database issues**:
```bash
# Check database location
echo $LEDGERLOOP_DATA_DIR

# Reset database (CAUTION: deletes all data)
rm ~/.ledgerloop/ledgerloop.duckdb
./start
```

**Import failures**:
- Check file format compatibility
- Verify file permissions
- Look for encoding issues (UTF-8 required)

**AI not working**:
- Check AI configuration in settings
- Verify local LLM setup
- Test with simple heuristic mode first

### Test Environment Reset
```bash
# Clean reset for testing
./start stop both
rm -rf ~/.ledgerloop
rm -rf apps/backend/.pytest_cache
rm -rf apps/web/tmp
./setup --clean
./start
```

## Test Reporting

### Success Criteria
Document for each test:
- ✅ Pass / ❌ Fail / ⚠️ Warning
- Execution time
- Error messages (if any)
- Screenshots for UI tests

### Performance Metrics
- Import speed (transactions/second)
- Memory usage patterns
- API response times
- Database query performance

### Bug Reports
Include:
1. Steps to reproduce
2. Expected vs actual behavior
3. System configuration
4. Error logs
5. Screenshots/videos if relevant

This test plan validates that LedgerLoop is production-ready and meets all specified requirements for a personal finance management application.
