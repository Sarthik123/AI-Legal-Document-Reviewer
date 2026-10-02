-- Preserve a failed document row so the UI can show its state and retry it.

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS processing_error VARCHAR(500);
