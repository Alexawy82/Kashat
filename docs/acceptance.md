V1 Acceptance Criteria (Proposed)

- Import (CSV):
  - Parse and normalize CSV from at least two institutions.
  - Idempotent re-import without creating duplicates.
- Normalization & Dedup:
  - Deterministic description canonicalization and date/amount parsing.
  - Unique fingerprint prevents duplicate inserts for same input.
- Classification Rules:
  - Manual category assignment.
  - Priority-ordered rules (regex on description, amount range, account filter).
- Detection:
  - Transfer detection: opposite-sign near-equal amount within N-day window; suggestions with scores; manual confirm/reject.
  - Recurring detection: monthly/weekly cadence heuristics; manual confirm.
- Dashboard:
  - Spend summary by month and category; basic merchant breakdown.
- Export:
  - CSV export of normalized transactions with categories and flags.
- Privacy:
  - No network calls; all local processing; audit log of changes.
