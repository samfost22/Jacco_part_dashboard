-- EU Parts Jobs Database Schema
-- This schema stores synchronized job data from Zuper API

-- Main jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_uid VARCHAR(255) PRIMARY KEY,
    job_number VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(500),
    description TEXT,
    job_status VARCHAR(100),
    job_category VARCHAR(100),
    priority VARCHAR(50),

    -- Customer information
    customer_name VARCHAR(255),
    customer_uid VARCHAR(255),

    -- Location information
    job_address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),

    -- Technician information
    assigned_technician VARCHAR(255),
    technician_uid VARCHAR(255),

    -- Timestamps
    scheduled_start_time TIMESTAMP,
    scheduled_end_time TIMESTAMP,
    actual_start_time TIMESTAMP,
    actual_end_time TIMESTAMP,
    created_time TIMESTAMP,
    modified_time TIMESTAMP,

    -- Parts information
    parts_status VARCHAR(100),
    parts_delivered_date TIMESTAMP,

    -- Additional metadata
    custom_fields JSONB,
    tags TEXT[],

    -- Sync tracking
    last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes for common queries
    CONSTRAINT valid_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT valid_longitude CHECK (longitude BETWEEN -180 AND 180)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(job_status);
CREATE INDEX IF NOT EXISTS idx_jobs_category ON jobs(job_category);
CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_jobs_scheduled_start ON jobs(scheduled_start_time);
CREATE INDEX IF NOT EXISTS idx_jobs_technician ON jobs(technician_uid);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_time);
CREATE INDEX IF NOT EXISTS idx_jobs_last_synced ON jobs(last_synced);

-- Parts inventory table (if needed)
CREATE TABLE IF NOT EXISTS parts_inventory (
    part_uid VARCHAR(255) PRIMARY KEY,
    part_number VARCHAR(100) UNIQUE NOT NULL,
    part_name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    quantity_available INTEGER DEFAULT 0,
    unit_price DECIMAL(10, 2),
    location VARCHAR(255),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job parts association table
CREATE TABLE IF NOT EXISTS job_parts (
    id SERIAL PRIMARY KEY,
    job_uid VARCHAR(255) REFERENCES jobs(job_uid) ON DELETE CASCADE,
    part_uid VARCHAR(255),
    part_number VARCHAR(100),
    part_name VARCHAR(255),
    quantity_required INTEGER,
    quantity_delivered INTEGER DEFAULT 0,
    status VARCHAR(50),
    created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_job FOREIGN KEY (job_uid) REFERENCES jobs(job_uid) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_parts_job ON job_parts(job_uid);
CREATE INDEX IF NOT EXISTS idx_job_parts_part ON job_parts(part_uid);

-- Sync log table for tracking API synchronization
CREATE TABLE IF NOT EXISTS sync_log (
    id SERIAL PRIMARY KEY,
    sync_started TIMESTAMP NOT NULL,
    sync_completed TIMESTAMP,
    status VARCHAR(50),
    jobs_fetched INTEGER,
    jobs_updated INTEGER,
    jobs_created INTEGER,
    errors TEXT,
    sync_duration_seconds INTEGER
);

CREATE INDEX IF NOT EXISTS idx_sync_log_started ON sync_log(sync_started DESC);

-- View for EU jobs only (within geographic bounds)
CREATE OR REPLACE VIEW eu_parts_jobs AS
SELECT *
FROM jobs
WHERE
    job_category = 'Field Requires Parts'
    AND latitude BETWEEN 35 AND 72
    AND longitude BETWEEN -11 AND 40
ORDER BY scheduled_start_time DESC;

-- View for active jobs needing parts
CREATE OR REPLACE VIEW active_parts_jobs AS
SELECT *
FROM eu_parts_jobs
WHERE
    job_status NOT IN ('Completed', 'Cancelled', 'Closed')
ORDER BY scheduled_start_time ASC;

-- Function to update last_synced timestamp
CREATE OR REPLACE FUNCTION update_last_synced()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_synced = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update last_synced
CREATE TRIGGER trigger_update_last_synced
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_last_synced();
