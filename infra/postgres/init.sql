-- Initial Postgres setup. Runs once on first container start.

-- Enable extensions used across the schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";      -- case-insensitive email
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- summoner name search

-- Optional: timezone
SET TIME ZONE 'UTC';
