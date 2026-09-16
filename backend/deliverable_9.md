CREATE TABLE failed_lead_events (
    id UUID PRIMARY KEY,
    original_event JSONB NOT NULL,
    failure_reason VARCHAR(500),
    error_details TEXT,
    failure_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    last_retry TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);