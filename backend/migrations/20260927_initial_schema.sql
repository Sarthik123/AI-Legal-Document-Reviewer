-- Initial production schema for Neon PostgreSQL + pgvector.
-- Apply once before starting the API. All statements are idempotent.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT TRUE,
    email_verification_token_hash VARCHAR(64),
    email_verification_expires_at TIMESTAMP,
    password_reset_token_hash VARCHAR(64),
    password_reset_expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    processing_status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    text_length INTEGER,
    analysis_json JSON,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_documents_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_document_chunks_document FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    document_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources_json JSON,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_chat_messages_document FOREIGN KEY (document_id)
        REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT fk_chat_messages_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_email_verification_token_hash
    ON users(email_verification_token_hash);
CREATE INDEX IF NOT EXISTS ix_users_password_reset_token_hash
    ON users(password_reset_token_hash);
CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id
    ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS ix_document_chunks_page_number
    ON document_chunks(page_number);
CREATE INDEX IF NOT EXISTS ix_chat_messages_document_id
    ON chat_messages(document_id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id
    ON chat_messages(user_id);
