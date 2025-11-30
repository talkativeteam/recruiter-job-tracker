-- Supabase Table Creation Script
-- Run this SQL in your Supabase SQL Editor

-- Create agent_logs table
CREATE TABLE IF NOT EXISTS agent_logs (
  id BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  agent_name TEXT NOT NULL,
  run_id TEXT UNIQUE NOT NULL,
  run_status TEXT NOT NULL,
  cost_of_run TEXT DEFAULT '$0.00',
  client_name TEXT,
  client_email TEXT,
  client_website TEXT,
  exa_webset TEXT,  -- Can be null
  icp TEXT,  -- JSON string of ICP data
  job_identified_by TEXT DEFAULT 'LinkedIn Jobs Scraper',  -- What we're scraping
  job_posting_links TEXT[],  -- Array of job URLs
  job_posting_date TIMESTAMP WITH TIME ZONE,  -- When jobs were posted
  phase TEXT,
  companies_found INT DEFAULT 0,
  companies_validated INT DEFAULT 0,
  final_companies_selected INT DEFAULT 0,
  error_message TEXT
);

-- Create index on run_id for fast lookups
CREATE INDEX IF NOT EXISTS idx_agent_logs_run_id ON agent_logs(run_id);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_agent_logs_created_at ON agent_logs(created_at DESC);

-- Create index on run_status for filtering
CREATE INDEX IF NOT EXISTS idx_agent_logs_run_status ON agent_logs(run_status);

-- Create index on agent_name for filtering
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent_name ON agent_logs(agent_name);

-- Enable Row Level Security (RLS)
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;

-- Create policy for service role (full access)
CREATE POLICY "Service role has full access" ON agent_logs
  FOR ALL
  USING (auth.role() = 'service_role');

-- Create policy for anon users (read-only access to own runs)
CREATE POLICY "Anon users can read their own runs" ON agent_logs
  FOR SELECT
  USING (true);

-- Optional: Create policy for authenticated users
CREATE POLICY "Authenticated users can read all" ON agent_logs
  FOR SELECT
  TO authenticated
  USING (true);

-- Verify table creation
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agent_logs'
ORDER BY ordinal_position;
