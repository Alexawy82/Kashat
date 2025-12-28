CREATE TABLE IF NOT EXISTS workflow_state (
    id TEXT PRIMARY KEY,
    type TEXT,
    status TEXT,
    state_json TEXT NOT NULL,
    created_ts TIMESTAMP NOT NULL,
    updated_ts TIMESTAMP NOT NULL
);
