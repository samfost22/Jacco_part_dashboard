-- EU Parts Jobs Database Schema (SQLite)
-- This schema stores synchronized job data from Zuper API

-- Main jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_uid TEXT PRIMARY KEY,
    job_number TEXT UNIQUE,  -- work_order_number from Zuper API, may be NULL
    title TEXT,
    description TEXT,
    job_status TEXT,
    job_category TEXT,
    priority TEXT,

    -- Customer information
    customer_name TEXT,
    customer_uid TEXT,

    -- Asset/Property information
    asset_name TEXT,
    asset_uid TEXT,

    -- Location information
    job_address TEXT,
    latitude REAL,
    longitude REAL,

    -- Technician information
    assigned_technician TEXT,
    technician_uid TEXT,

    -- Timestamps (stored as TEXT in ISO8601 format)
    scheduled_start_time TEXT,
    scheduled_end_time TEXT,
    actual_start_time TEXT,
    actual_end_time TEXT,
    created_time TEXT,
    modified_time TEXT,

    -- Parts information
    parts_status TEXT,
    parts_delivered_date TEXT,

    -- Additional metadata (JSON as TEXT)
    custom_fields TEXT,
    tags TEXT,

    -- Sync tracking
    last_synced TEXT DEFAULT (datetime('now')),

    -- Constraints for valid coordinates
    CHECK (latitude IS NULL OR (latitude BETWEEN -90 AND 90)),
    CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180))
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_job_number ON jobs(job_number);
CREATE INDEX IF NOT EXISTS idx_job_status ON jobs(job_status);
CREATE INDEX IF NOT EXISTS idx_job_category ON jobs(job_category);
CREATE INDEX IF NOT EXISTS idx_customer_name ON jobs(customer_name);
CREATE INDEX IF NOT EXISTS idx_scheduled_start ON jobs(scheduled_start_time);
CREATE INDEX IF NOT EXISTS idx_location ON jobs(latitude, longitude);

-- Sync log table to track synchronization operations
CREATE TABLE IF NOT EXISTS sync_log (
    sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_started TEXT DEFAULT (datetime('now')),
    sync_completed TEXT,
    status TEXT,  -- 'running', 'completed', 'failed'
    jobs_fetched INTEGER DEFAULT 0,
    jobs_created INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    jobs_skipped INTEGER DEFAULT 0,
    errors TEXT,  -- JSON array of errors
    notes TEXT
);

-- Create index on sync log
CREATE INDEX IF NOT EXISTS idx_sync_started ON sync_log(sync_started DESC);
