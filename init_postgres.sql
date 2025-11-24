-- PrimalCore PostgreSQL Initialization
-- Creates the events table for the 10-database pipeline

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP NOT NULL,
    key VARCHAR(255) NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups by key and timestamp
CREATE INDEX IF NOT EXISTS idx_events_key_ts ON events(key, ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);

-- Optional: Create a view for recent events
CREATE OR REPLACE VIEW recent_events AS
SELECT * FROM events
ORDER BY ts DESC
LIMIT 1000;

-- Insert a test event
INSERT INTO events (ts, key, value, metadata) VALUES
(NOW(), 'system_init', 1.0, '{"source": "init_script", "batch": 2}');

-- Verify
SELECT COUNT(*) as total_events FROM events;
