-- Additive: a short reason code (e.g. "ocr_failed") when processing fails, and
-- when the current processing attempt started (to detect interrupted attempts).
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS processing_error VARCHAR(50);

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMP;
