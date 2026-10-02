-- Durable document-processing queue. Apply after the existing migrations.

CREATE TABLE IF NOT EXISTS document_jobs (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_document_jobs_document FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_document_jobs_status_available_at
    ON document_jobs(status, available_at);
