-- 1. Create a schema for better organization (Optional but recommended)
-- CREATE SCHEMA IF NOT EXISTS cap_group_schema;

-- 2. Tasks Audit Table
-- Tracks the status of every background job triggered by the API
CREATE TABLE IF NOT EXISTS task_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    task_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

-- 3. Scraped Data Table
-- Stores the raw content captured by the Selenium workers
CREATE TABLE IF NOT EXISTS raw_scraped_data (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) REFERENCES task_logs(task_id),
    url TEXT NOT NULL,
    raw_html_path TEXT, -- Link to S3 file containing the full HTML
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB      -- Flexible storage for headers, tags, etc.
);

-- 4. Extracted/Transformed Data Table
-- Stores the final, cleaned data ready for business use
CREATE TABLE IF NOT EXISTS processed_records (
    id SERIAL PRIMARY KEY,
    reference_id VARCHAR(100),
    data_payload JSONB NOT NULL,
    is_validated BOOLEAN DEFAULT FALSE,
    validation_errors JSONB,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for performance
CREATE INDEX IF NOT EXISTS idx_task_status ON task_logs(status);
CREATE INDEX IF NOT EXISTS idx_processed_valid ON processed_records(is_validated);



