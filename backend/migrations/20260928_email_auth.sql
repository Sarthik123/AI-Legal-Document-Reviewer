-- Preserve existing accounts by marking them verified during the additive migration.
-- New registrations explicitly set email_verified = false in the application.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verification_token_hash VARCHAR(64);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMP;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_reset_token_hash VARCHAR(64);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS ix_users_email_verification_token_hash
    ON users (email_verification_token_hash);

CREATE INDEX IF NOT EXISTS ix_users_password_reset_token_hash
    ON users (password_reset_token_hash);
