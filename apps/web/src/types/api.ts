import { Database } from './supabase'

// Type aliases for easier usage
export type ApiKey = Database['public']['Tables']['api_keys']['Row']
export type CreditBalance = Database['public']['Tables']['credit_balance']['Row']
export type UsageLog = Database['public']['Tables']['usage_logs']['Row']
export type Render = Database['public']['Tables']['renders']['Row']
export type StripeCustomer = Database['public']['Tables']['stripe_customers']['Row']

// API Request/Response types
export interface CreateApiKeyRequest {
  name: string
}

export interface CreateApiKeyResponse {
  id: string
  name: string
  key: string // Only returned once
  created_at: string
}

export interface ApiKeyListResponse {
  id: string
  name: string
  created_at: string
  last_used: string | null
  is_active: boolean
}

export interface TokenPurchaseRequest {
  amount: number // in USD cents
  token_count: number
}

export interface TokenPurchaseResponse {
  payment_intent_id: string
  client_secret: string
}

export interface UsageStatsQuery {
  period?: 'day' | 'week' | 'month' | 'year'
  start_date?: string
  end_date?: string
  limit?: number
}

export interface UsageStatsResponse {
  total_requests: number
  tokens_consumed: number
  period_start: string
  period_end: string
  by_endpoint: Array<{
    endpoint: string
    count: number
    tokens: number
  }>
}

export interface UserProfileResponse {
  id: string
  email: string
  created_at: string
  token_balance: number
  total_usage: number
}

// Error response type
export interface ApiError {
  error: string
  code?: string
  details?: any
}