-- =============================================================================
-- SUPABASE SCHEMA FOR SHOTSTACK INTERMEDIARY PLATFORM
-- =============================================================================
-- Run this in your Supabase SQL Editor to set up the database schema

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- TABLES
-- =============================================================================

-- API Keys table for user-generated API keys
CREATE TABLE IF NOT EXISTS api_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  key_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_used TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT true,
  
  -- Indexes
  CONSTRAINT api_keys_name_user_unique UNIQUE(user_id, name)
);

-- Credit balance table for token management
CREATE TABLE IF NOT EXISTS credit_balance (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage logs table for tracking API usage
CREATE TABLE IF NOT EXISTS usage_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
  endpoint VARCHAR(255) NOT NULL,
  tokens_consumed INTEGER NOT NULL DEFAULT 0,
  request_data JSONB,
  response_status INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Renders table for tracking video rendering jobs
CREATE TABLE IF NOT EXISTS renders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id VARCHAR(255) NOT NULL UNIQUE,
  status VARCHAR(50) NOT NULL DEFAULT 'queued',
  shotstack_url TEXT,
  gcs_url TEXT,
  metadata JSONB,
  tokens_consumed INTEGER DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stripe customers table for payment integration
CREATE TABLE IF NOT EXISTS stripe_customers (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- API Keys indexes
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- Usage logs indexes
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_logs_api_key_id ON usage_logs(api_key_id);

-- Renders indexes
CREATE INDEX IF NOT EXISTS idx_renders_user_id ON renders(user_id);
CREATE INDEX IF NOT EXISTS idx_renders_job_id ON renders(job_id);
CREATE INDEX IF NOT EXISTS idx_renders_status ON renders(status);
CREATE INDEX IF NOT EXISTS idx_renders_created_at ON renders(created_at);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE renders ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_customers ENABLE ROW LEVEL SECURITY;

-- API Keys policies
CREATE POLICY "Users can view their own API keys" ON api_keys
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own API keys" ON api_keys
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own API keys" ON api_keys
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own API keys" ON api_keys
  FOR DELETE USING (auth.uid() = user_id);

-- Credit balance policies
CREATE POLICY "Users can view their own balance" ON credit_balance
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own balance" ON credit_balance
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role can update any balance" ON credit_balance
  FOR UPDATE USING (auth.jwt() ->> 'role' = 'service_role');

-- Usage logs policies
CREATE POLICY "Users can view their own usage logs" ON usage_logs
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert usage logs" ON usage_logs
  FOR INSERT WITH CHECK (auth.jwt() ->> 'role' = 'service_role');

-- Renders policies
CREATE POLICY "Users can view their own renders" ON renders
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all renders" ON renders
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Stripe customers policies
CREATE POLICY "Users can view their own stripe data" ON stripe_customers
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage stripe data" ON stripe_customers
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to automatically create credit balance for new users
CREATE OR REPLACE FUNCTION create_user_credit_balance()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO credit_balance (user_id, balance)
  VALUES (NEW.id, 0);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create credit balance on user signup
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION create_user_credit_balance();

-- Function to update credit balance timestamp
CREATE OR REPLACE FUNCTION update_credit_balance_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for credit balance updates
CREATE OR REPLACE TRIGGER update_credit_balance_updated_at
  BEFORE UPDATE ON credit_balance
  FOR EACH ROW EXECUTE FUNCTION update_credit_balance_timestamp();

-- Function to update renders timestamp
CREATE OR REPLACE FUNCTION update_renders_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for renders updates
CREATE OR REPLACE TRIGGER update_renders_updated_at
  BEFORE UPDATE ON renders
  FOR EACH ROW EXECUTE FUNCTION update_renders_timestamp();

-- =============================================================================
-- VIEWS (Optional - for analytics)
-- =============================================================================

-- View for user statistics
CREATE OR REPLACE VIEW user_stats AS
SELECT 
  u.id as user_id,
  u.email,
  u.created_at as user_created_at,
  cb.balance as current_balance,
  COUNT(DISTINCT ak.id) as api_keys_count,
  COUNT(DISTINCT r.id) as total_renders,
  COALESCE(SUM(ul.tokens_consumed), 0) as total_tokens_consumed,
  MAX(ul.created_at) as last_api_usage
FROM auth.users u
LEFT JOIN credit_balance cb ON u.id = cb.user_id
LEFT JOIN api_keys ak ON u.id = ak.user_id AND ak.is_active = true
LEFT JOIN renders r ON u.id = r.user_id
LEFT JOIN usage_logs ul ON u.id = ul.user_id
GROUP BY u.id, u.email, u.created_at, cb.balance;

-- Grant access to the view
GRANT SELECT ON user_stats TO authenticated;
GRANT SELECT ON user_stats TO service_role;

-- =============================================================================
-- INITIAL DATA (Optional)
-- =============================================================================

-- You can add any initial data here if needed
-- For example, default token packages, etc.

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

-- If you see this comment, the schema has been successfully applied!
-- Next steps:
-- 1. Verify all tables were created in the Supabase dashboard
-- 2. Test the RLS policies work correctly
-- 3. Update your application's environment variables
-- 4. Test user registration and API key generation