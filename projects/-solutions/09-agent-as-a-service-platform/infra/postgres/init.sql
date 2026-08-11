-- =============================================================================
-- Postgres init script — runs once when the data volume is empty.
-- =============================================================================
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- The schema itself is managed by Alembic migrations (backend/alembic/versions).
-- This file just makes sure the extensions we rely on are present.

-- Helpful default
SET timezone TO 'UTC';
