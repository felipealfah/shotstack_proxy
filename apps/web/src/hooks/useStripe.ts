/**
 * Stripe Integration Hook
 * Handles token package purchases and transaction management
 */

import { useState, useCallback } from 'react'
import { supabase } from '@/integrations/supabase/client'
import { useToast } from '@/hooks/use-toast'

export interface TokenPackage {
  type: 'starter' | 'standard' | 'pro' | 'business'
  tokens: number
  amount_cents: number
  amount_usd: number
  description: string
  recommended: boolean
}

export interface CreateCheckoutResponse {
  success: boolean
  session_id: string
  checkout_url: string
  expires_at?: number
  amount_total?: number
  currency: string
}

export interface TransactionHistory {
  id: string
  package_type: string
  tokens_purchased: number
  amount_cents: number
  amount_usd: number
  status: string
  created_at: string
  completed_at?: string
}

export interface TransactionHistoryResponse {
  success: boolean
  transactions: TransactionHistory[]
  total_transactions: number
  total_spent_usd: number
  total_tokens_purchased: number
}

export function useStripe() {
  const [packages, setPackages] = useState<TokenPackage[]>([])
  const [transactions, setTransactions] = useState<TransactionHistory[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  // Get current user session
  const getCurrentUser = async () => {
    const { data: { session } } = await supabase.auth.getSession()
    return session
  }

  // Get API headers for authenticated requests
  const getApiHeaders = async () => {
    const session = await getCurrentUser()
    if (!session) {
      throw new Error('User not authenticated')
    }

    // Get user's active API key
    // Note: We're temporarily using key_hash instead of api_key for debugging
    const { data: apiKeys, error: keyError } = await supabase
      .from('api_keys')
      .select('key_hash, api_key')
      .eq('user_id', session.user.id)
      .eq('is_active', true)
      .limit(1)

    if (keyError) {
      console.error('Supabase error:', keyError)
      throw new Error(`Database error: ${keyError.message}`)
    }

    if (!apiKeys?.length) {
      console.log('No API keys found for user:', session.user.id)
      throw new Error('No active API key found. Please create an API key first.')
    }

    console.log('Found API key:', { hasApiKey: !!apiKeys[0].api_key, hasKeyHash: !!apiKeys[0].key_hash })
    
    // Use api_key if available, otherwise use key_hash (temporary fallback)
    const keyToUse = apiKeys[0].api_key || apiKeys[0].key_hash
    
    if (!keyToUse) {
      throw new Error('API key data is corrupted. Please create a new API key.')
    }

    return {
      'Authorization': `Bearer ${keyToUse}`,
      'X-User-Email': session.user.email || '',
      'Content-Type': 'application/json'
    }
  }

  // Fetch available token packages
  const fetchPackages = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const headers = await getApiHeaders()
      
      const response = await fetch('http://localhost:8002/api/v1/stripe/packages', {
        method: 'GET',
        headers
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch packages: ${response.status}`)
      }

      const data = await response.json()
      setPackages(data.packages || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch packages'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Create Stripe checkout session
  const createCheckoutSession = useCallback(async (
    packageType: string,
    successUrl?: string,
    cancelUrl?: string
  ): Promise<string | null> => {
    setLoading(true)
    setError(null)

    try {
      const headers = await getApiHeaders()

      const requestBody = {
        package_type: packageType,
        success_url: successUrl || `${window.location.origin}/payment/success`,
        cancel_url: cancelUrl || `${window.location.origin}/payment/cancel`
      }

      const response = await fetch('http://localhost:8002/api/v1/stripe/create-checkout-session', {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `Failed to create checkout session: ${response.status}`)
      }

      const data: CreateCheckoutResponse = await response.json()
      
      if (!data.success) {
        throw new Error('Failed to create checkout session')
      }

      toast({
        title: "Redirecting to payment...",
        description: "You'll be redirected to Stripe Checkout to complete your purchase.",
      })

      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url
      
      return data.session_id
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create checkout session'
      setError(errorMessage)
      toast({
        title: "Payment Error",
        description: errorMessage,
        variant: "destructive"
      })
      return null
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Fetch transaction history
  const fetchTransactionHistory = useCallback(async (limit = 20, offset = 0) => {
    setLoading(true)
    setError(null)

    try {
      const headers = await getApiHeaders()
      
      const response = await fetch(
        `http://localhost:8002/api/v1/stripe/transactions?limit=${limit}&offset=${offset}`, 
        {
          method: 'GET',
          headers
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch transactions: ${response.status}`)
      }

      const data: TransactionHistoryResponse = await response.json()
      setTransactions(data.transactions || [])
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch transaction history'
      setError(errorMessage)
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive"
      })
      return null
    } finally {
      setLoading(false)
    }
  }, [toast])

  // Get session status
  const getSessionStatus = useCallback(async (sessionId: string) => {
    try {
      const headers = await getApiHeaders()
      
      const response = await fetch(`http://localhost:8002/api/v1/stripe/session/${sessionId}`, {
        method: 'GET',
        headers
      })

      if (!response.ok) {
        throw new Error(`Failed to get session status: ${response.status}`)
      }

      const data = await response.json()
      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get session status'
      setError(errorMessage)
      return null
    }
  }, [])

  return {
    // State
    packages,
    transactions,
    loading,
    error,
    
    // Actions
    fetchPackages,
    createCheckoutSession,
    fetchTransactionHistory,
    getSessionStatus,
    
    // Utilities
    getCurrentUser
  }
}