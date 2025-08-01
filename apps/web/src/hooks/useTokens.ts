'use client'

import { useState, useEffect } from 'react'
import { CreditBalance, TokenPurchaseRequest } from '@/types/api'

export function useTokens() {
  const [balance, setBalance] = useState<CreditBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchBalance = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/tokens/balance')
      
      if (!response.ok) {
        throw new Error('Failed to fetch token balance')
      }
      
      const data = await response.json()
      setBalance(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const purchaseTokens = async (request: TokenPurchaseRequest) => {
    const response = await fetch('/api/tokens/purchase', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to initiate token purchase')
    }

    return response.json()
  }

  useEffect(() => {
    fetchBalance()
  }, [])

  return {
    balance,
    loading,
    error,
    purchaseTokens,
    refresh: fetchBalance
  }
}