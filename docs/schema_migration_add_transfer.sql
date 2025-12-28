-- Schema Migration: Add is_transfer column to transaction table
-- Version: 5 - Enhanced AI + Detection Integration

-- Add the is_transfer column if it doesn't exist
ALTER TABLE transaction ADD COLUMN IF NOT EXISTS is_transfer BOOLEAN DEFAULT FALSE;

-- Update schema version
INSERT OR IGNORE INTO schema_version (version, description) VALUES 
(5, 'Added is_transfer detection marker for AI integration');

-- Create index for performance on detection queries
CREATE INDEX IF NOT EXISTS idx_tx_detection_markers ON transaction(is_income, is_transfer, is_adjustment);

-- Update any existing transfer-like transactions
UPDATE transaction 
SET is_transfer = TRUE 
WHERE description_norm ILIKE '%transfer%' 
   OR description_norm ILIKE '%keep the change%'
   OR description_norm ILIKE '%online banking transfer%';

-- Log the migration
INSERT INTO event_log (id, entity_type, entity_id, action, payload_json, ts, actor) 
VALUES (
    lower(hex(randomblob(16))),
    'schema',
    'transaction',
    'add_transfer_column',
    '{"column": "is_transfer", "type": "BOOLEAN", "default": false}',
    CURRENT_TIMESTAMP,
    'migration_script'
);