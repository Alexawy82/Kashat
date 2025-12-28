-- Add normalized_name column for categories and enforce uniqueness.
BEGIN TRANSACTION;

-- Add column if missing
ALTER TABLE category ADD COLUMN IF NOT EXISTS normalized_name TEXT;

-- Backfill normalized values
UPDATE category
SET normalized_name = lower(trim(name))
WHERE normalized_name IS NULL;

-- Build canonical mapping per normalized name
CREATE TEMP TABLE _cat_canon AS
SELECT normalized_name, MIN(id) AS canonical_id
FROM category
GROUP BY normalized_name;

-- Repoint transaction_category to canonical ids
UPDATE transaction_category AS tc
SET category_id = c2.canonical_id
FROM _cat_canon c2
JOIN category c ON c.id = tc.category_id
WHERE c.normalized_name = c2.normalized_name
  AND tc.category_id <> c2.canonical_id;

-- Delete duplicate category rows (keep canonical only)
DELETE FROM category
WHERE id NOT IN (SELECT canonical_id FROM _cat_canon);

-- Ensure uniqueness on normalized_name
CREATE UNIQUE INDEX IF NOT EXISTS ux_category_normalized ON category(normalized_name);

COMMIT;

