-- Migration Script: Add Enhanced Logging Columns
-- Run this in Supabase SQL Editor if you already created the table
-- This adds the new columns to capture ICP, job links, dates, etc.

-- Add new columns to existing agent_logs table
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS client_email TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS client_website TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS exa_webset TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS icp TEXT;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_identified_by TEXT DEFAULT 'LinkedIn Jobs Scraper';
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_posting_links TEXT[];
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS job_posting_date TIMESTAMP WITH TIME ZONE;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS companies_found INTEGER DEFAULT 0;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS companies_validated INTEGER DEFAULT 0;
ALTER TABLE agent_logs ADD COLUMN IF NOT EXISTS final_companies_selected INTEGER DEFAULT 0;

-- Verify new columns were added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'agent_logs'
  AND column_name IN ('client_website', 'exa_webset', 'icp', 'job_identified_by', 'job_posting_links', 'job_posting_date')
ORDER BY column_name;

-- Show all columns to confirm
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'agent_logs'
ORDER BY ordinal_position;
