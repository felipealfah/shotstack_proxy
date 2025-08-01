-- =============================================================================
-- SUPABASE SCHEMA FOR SHOTSTACK INTERMEDIARY PLATFORM - UPDATED
-- =============================================================================
-- Run this in your Supabase SQL Editor to set up the database schema
-- Updated to match BUSINESS_RULES.md specifications

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
  name VARCHAR(50) NOT NULL, -- Max 50 chars per business rules
  key_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  last_used TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN DEFAULT true,
  
  -- Constraints per business rules
  CONSTRAINT api_keys_name_user_unique UNIQUE(user_id, name),
  CONSTRAINT api_keys_name_length CHECK (LENGTH(name) <= 50)
);

-- Credit balance table for token management
CREATE TABLE IF NOT EXISTS credit_balance (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  balance INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0), -- No negative balance allowed
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Usage logs table for tracking API usage
CREATE TABLE IF NOT EXISTS usage_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
  endpoint VARCHAR(255) NOT NULL,
  tokens_consumed INTEGER NOT NULL DEFAULT 0,
  video_duration_seconds INTEGER, -- NEW: For 1 token = 1 minute calculation
  request_data JSONB,
  response_status INTEGER,
  error_code VARCHAR(50), -- NEW: Standardized error codes
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Renders table for tracking video rendering jobs
CREATE TABLE IF NOT EXISTS renders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  job_id VARCHAR(255) NOT NULL UNIQUE,
  status VARCHAR(50) NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'cancelled')),
  shotstack_url TEXT,
  gcs_url TEXT,
  video_duration_seconds INTEGER, -- NEW: For token calculation
  tokens_consumed INTEGER DEFAULT 0,
  tokens_refunded INTEGER DEFAULT 0, -- NEW: Track refunds
  metadata JSONB,
  error_message TEXT, -- NEW: Store error details
  retry_count INTEGER DEFAULT 0, -- NEW: Track retries
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE -- NEW: Track completion time
);

-- Stripe customers table for payment integration
CREATE TABLE IF NOT EXISTS stripe_customers (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- NEW: Token transactions table for detailed financial tracking
CREATE TABLE IF NOT EXISTS token_transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('purchase', 'debit', 'refund')),
  amount INTEGER NOT NULL, -- Positive for credits, negative for debits
  balance_before INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  reference_id UUID, -- References render.id or stripe payment
  description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- NEW: API Key limits and quotas
CREATE TABLE IF NOT EXISTS api_key_quotas (
  api_key_id UUID PRIMARY KEY REFERENCES api_keys(id) ON DELETE CASCADE,
  hourly_limit INTEGER DEFAULT 100, -- Requests per hour
  concurrent_jobs_limit INTEGER DEFAULT 5, -- Max simultaneous renders
  max_video_duration_minutes INTEGER DEFAULT 10, -- Max video length
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- NEW: Rate limiting tracking
CREATE TABLE IF NOT EXISTS rate_limit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  requests_count INTEGER DEFAULT 1,
  window_start TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- CONSTRAINTS AND BUSINESS RULES
-- =============================================================================

-- Limit API keys per user (max 10 active)
CREATE OR REPLACE FUNCTION check_api_key_limit()
RETURNS TRIGGER AS $$
BEGIN
  IF (SELECT COUNT(*) FROM api_keys WHERE user_id = NEW.user_id AND is_active = true) >= 10 THEN
    RAISE EXCEPTION 'Maximum of 10 active API keys per user allowed';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_api_key_limit
  BEFORE INSERT ON api_keys
  FOR EACH ROW EXECUTE FUNCTION check_api_key_limit();

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
CREATE INDEX IF NOT EXISTS idx_usage_logs_endpoint ON usage_logs(endpoint);

-- Renders indexes
CREATE INDEX IF NOT EXISTS idx_renders_user_id ON renders(user_id);
CREATE INDEX IF NOT EXISTS idx_renders_job_id ON renders(job_id);
CREATE INDEX IF NOT EXISTS idx_renders_status ON renders(status);
CREATE INDEX IF NOT EXISTS idx_renders_created_at ON renders(created_at);

-- NEW: Token transactions indexes
CREATE INDEX IF NOT EXISTS idx_token_transactions_user_id ON token_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_token_transactions_type ON token_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_token_transactions_created_at ON token_transactions(created_at);

-- NEW: Rate limiting indexes
CREATE INDEX IF NOT EXISTS idx_rate_limit_api_key_window ON rate_limit_log(api_key_id, window_start);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE credit_balance ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE renders ENABLE ROW LEVEL SECURITY;
ALTER TABLE stripe_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_quotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_log ENABLE ROW LEVEL SECURITY;

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

-- Token transactions policies
CREATE POLICY "Users can view their own token transactions" ON token_transactions
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage token transactions" ON token_transactions
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- API key quotas policies
CREATE POLICY "Users can view their own API key quotas" ON api_key_quotas
  FOR SELECT USING (auth.uid() = (SELECT user_id FROM api_keys WHERE id = api_key_id));

CREATE POLICY "Service role can manage API key quotas" ON api_key_quotas
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Rate limit log policies (service role only)
CREATE POLICY "Service role can manage rate limit logs" ON rate_limit_log
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

-- Function to calculate tokens based on video duration (1 token = 1 minute)
CREATE OR REPLACE FUNCTION calculate_tokens_for_duration(duration_seconds INTEGER)
RETURNS INTEGER AS $$
BEGIN
  -- Ceiling of minutes (any partial minute counts as full minute)
  RETURN CEIL(duration_seconds::DECIMAL / 60);
END;
$$ LANGUAGE plpgsql;

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

-- Function to automatically create API key quotas for new keys
CREATE OR REPLACE FUNCTION create_api_key_quotas()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO api_key_quotas (api_key_id)
  VALUES (NEW.id);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create quotas for new API keys
CREATE OR REPLACE TRIGGER on_api_key_created
  AFTER INSERT ON api_keys
  FOR EACH ROW EXECUTE FUNCTION create_api_key_quotas();

-- Function to log token transactions
CREATE OR REPLACE FUNCTION log_token_transaction(
  p_user_id UUID,
  p_transaction_type VARCHAR(20),
  p_amount INTEGER,
  p_reference_id UUID DEFAULT NULL,
  p_description TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
  current_balance INTEGER;
  new_balance INTEGER;
BEGIN
  -- Get current balance
  SELECT balance INTO current_balance 
  FROM credit_balance 
  WHERE user_id = p_user_id;
  
  -- Calculate new balance
  new_balance := current_balance + p_amount;
  
  -- Insert transaction log
  INSERT INTO token_transactions (
    user_id, 
    transaction_type, 
    amount, 
    balance_before, 
    balance_after, 
    reference_id, 
    description
  )
  VALUES (
    p_user_id, 
    p_transaction_type, 
    p_amount, 
    current_balance, 
    new_balance, 
    p_reference_id, 
    p_description
  );
  
  -- Update balance
  UPDATE credit_balance 
  SET balance = new_balance 
  WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS (Analytics and Reporting)
-- =============================================================================

-- View for user statistics (updated with new fields)
CREATE OR REPLACE VIEW user_stats AS
SELECT 
  u.id as user_id,
  u.email,
  u.created_at as user_created_at,
  u.email_confirmed_at IS NOT NULL as is_verified,
  cb.balance as current_balance,
  COUNT(DISTINCT ak.id) FILTER (WHERE ak.is_active = true) as active_api_keys_count,
  COUNT(DISTINCT r.id) as total_renders,
  COUNT(DISTINCT r.id) FILTER (WHERE r.status = 'completed') as successful_renders,
  COALESCE(SUM(ul.tokens_consumed), 0) as total_tokens_consumed,
  COALESCE(SUM(r.video_duration_seconds), 0) as total_video_seconds_rendered,
  MAX(ul.created_at) as last_api_usage,
  MAX(r.created_at) as last_render_date
FROM auth.users u
LEFT JOIN credit_balance cb ON u.id = cb.user_id
LEFT JOIN api_keys ak ON u.id = ak.user_id
LEFT JOIN renders r ON u.id = r.user_id
LEFT JOIN usage_logs ul ON u.id = ul.user_id
GROUP BY u.id, u.email, u.created_at, u.email_confirmed_at, cb.balance;

-- Grant access to the view
GRANT SELECT ON user_stats TO authenticated;
GRANT SELECT ON user_stats TO service_role;

-- View for render statistics
CREATE OR REPLACE VIEW render_stats AS
SELECT 
  status,
  COUNT(*) as count,
  AVG(video_duration_seconds) as avg_duration_seconds,
  SUM(tokens_consumed) as total_tokens_consumed,
  AVG(tokens_consumed) as avg_tokens_consumed
FROM renders
GROUP BY status;

GRANT SELECT ON render_stats TO service_role;

-- =============================================================================
-- INITIAL DATA AND CONFIGURATION
-- =============================================================================

-- Create default rate limiting configuration
CREATE TABLE IF NOT EXISTS system_config (
  key VARCHAR(100) PRIMARY KEY,
  value JSONB NOT NULL,
  description TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default configuration
INSERT INTO system_config (key, value, description) VALUES
('rate_limits', '{"global_per_minute": 1000, "per_ip_per_minute": 60, "per_user_per_hour": 100, "per_api_key_per_hour": 100}', 'System-wide rate limiting configuration'),
('token_pricing', '{"packages": [{"tokens": 60, "price_cents": 500}, {"tokens": 300, "price_cents": 2000}, {"tokens": 600, "price_cents": 3500}, {"tokens": 3000, "price_cents": 15000}, {"tokens": 6000, "price_cents": 25000}]}', 'Token packages and pricing in cents'),
('render_limits', '{"max_concurrent_per_user": 5, "max_video_duration_minutes": 10, "max_payload_size_mb": 10}', 'Rendering limits and quotas')
ON CONFLICT (key) DO NOTHING;

-- Enable RLS for system_config
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

-- Only service role can manage system config
CREATE POLICY "Service role can manage system config" ON system_config
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- COMPLETION MESSAGE
-- =============================================================================

-- If you see this comment, the schema has been successfully applied!
-- Next steps:
-- 1. Verify all tables were created in the Supabase dashboard
-- 2. Test the RLS policies work correctly
-- 3. Update your application's environment variables
-- 4. Test user registration and API key generation
-- 5. Test token calculation functions with video durations