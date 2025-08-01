-- Initial database setup for development
-- This file is used by Docker to initialize the PostgreSQL database

-- Create the main database (if not exists)
-- The database name is already created by the POSTGRES_DB environment variable

-- Create basic extensions that might be needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Note: In production, we use Supabase managed PostgreSQL
-- This file is only for local development with Docker