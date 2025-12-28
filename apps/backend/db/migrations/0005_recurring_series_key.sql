-- Add stable recurring series key + friendly display label.
-- Keeps suggest() idempotent and allows safe deduplication.

ALTER TABLE recurring_series ADD COLUMN series_key TEXT;
ALTER TABLE recurring_series ADD COLUMN display_name TEXT;

-- Backfill display_name (best-effort; refined in app logic as needed).
UPDATE recurring_series
SET display_name = name
WHERE display_name IS NULL OR trim(display_name) = '';

-- Backfill series_key based on (name, cadence, round(amount_mean, 2)).
-- Use cents integer for stable rounding across runtimes.
UPDATE recurring_series
SET series_key = md5(
  COALESCE(name, '') || '|' ||
  COALESCE(cadence, '') || '|' ||
  CAST(ROUND(COALESCE(amount_mean, 0) * 100) AS BIGINT)
)
WHERE series_key IS NULL OR trim(series_key) = '';

-- Merge duplicates by series_key (keep best candidate; merge memberships).
CREATE TEMP TABLE _rs_rank AS
SELECT
  rs.id,
  rs.series_key,
  CASE
    WHEN rs.status = 'confirmed' THEN 3
    WHEN rs.status = 'pending' THEN 2
    WHEN rs.status = 'rejected' THEN 1
    ELSE 0
  END AS status_rank,
  COALESCE(ct.cnt, 0) AS tx_cnt,
  rs.decided_at
FROM recurring_series rs
LEFT JOIN (SELECT series_id, COUNT(*) AS cnt FROM recurring_tx GROUP BY series_id) ct
  ON ct.series_id = rs.id
WHERE rs.series_key IS NOT NULL AND trim(rs.series_key) <> '';

CREATE TEMP TABLE _rs_keep AS
SELECT series_key, id AS keep_id
FROM (
  SELECT
    *,
    row_number() OVER (
      PARTITION BY series_key
      ORDER BY status_rank DESC, tx_cnt DESC, decided_at DESC NULLS LAST, id DESC
    ) AS rn
  FROM _rs_rank
) t
WHERE rn = 1;

-- Merge memberships from non-kept series into kept series.
INSERT INTO recurring_tx (series_id, tx_id)
SELECT k.keep_id AS series_id, rtx.tx_id
FROM recurring_tx rtx
JOIN _rs_rank r ON r.id = rtx.series_id
JOIN _rs_keep k ON k.series_key = r.series_key
WHERE r.id <> k.keep_id
ON CONFLICT DO NOTHING;

-- Drop non-kept series and their memberships.
DELETE FROM recurring_tx
WHERE series_id IN (
  SELECT id FROM _rs_rank WHERE id NOT IN (SELECT keep_id FROM _rs_keep)
);

DELETE FROM recurring_series
WHERE id IN (
  SELECT id FROM _rs_rank WHERE id NOT IN (SELECT keep_id FROM _rs_keep)
);

DROP TABLE _rs_rank;
DROP TABLE _rs_keep;

-- Enforce idempotency: one series per key.
CREATE UNIQUE INDEX IF NOT EXISTS ux_recurring_series_key ON recurring_series(series_key);

