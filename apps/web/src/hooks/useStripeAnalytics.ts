/**
 * Stripe Analytics Hook
 * Uses secure functions instead of views for analytics data
 */

import { useState, useCallback } from 'react'
import { supabase } from '@/integrations/supabase/client'
import { useToast } from '@/hooks/use-toast'

export interface DailyRevenue {
  date: string
  completed_transactions: number
  revenue_cents: number
  revenue_usd: number
  tokens_sold: number
  avg_order_value_usd: number
}

export interface MonthlyRevenue {
  month: string
  completed_transactions: number
  revenue_cents: number
  revenue_usd: number
  tokens_sold: number
  avg_order_value_usd: number
}

export interface PackageAnalytics {
  package_type: string
  total_purchases: number
  completed_purchases: number
  pending_purchases: number
  failed_purchases: number
  tokens_sold: number
  revenue_cents: number
  avg_order_value_usd: number
}

export interface UserStripeStats {
  total_spent_usd: number
  total_tokens_purchased: number
  total_transactions: number
  first_purchase_date: string | null
}

export function useStripeAnalytics() {
  const [dailyRevenue, setDailyRevenue] = useState<DailyRevenue[]>([])
  const [monthlyRevenue, setMonthlyRevenue] = useState<MonthlyRevenue[]>([])
  const [packageAnalytics, setPackageAnalytics] = useState<PackageAnalytics[]>([])
  const [userStats, setUserStats] = useState<UserStripeStats | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  // Fetch daily revenue analytics
  const fetchDailyRevenue = useCallback(async (daysBack = 30) => {
    setLoading(true)
    setError(null)

    try {
      const { data, error } = await supabase.rpc('get_daily_stripe_revenue', {
        days_back: daysBack
      })

      if (error) {
        throw error
      }

      setDailyRevenue(data || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch daily revenue'
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

  // Fetch monthly revenue analytics
  const fetchMonthlyRevenue = useCallback(async (monthsBack = 12) => {
    setLoading(true)
    setError(null)

    try {
      const { data, error } = await supabase.rpc('get_monthly_stripe_revenue', {
        months_back: monthsBack
      })

      if (error) {
        throw error
      }

      setMonthlyRevenue(data || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch monthly revenue'
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

  // Fetch package analytics
  const fetchPackageAnalytics = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const { data, error } = await supabase.rpc('get_stripe_package_analytics')

      if (error) {
        throw error
      }

      setPackageAnalytics(data || [])
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch package analytics'
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

  // Fetch user statistics
  const fetchUserStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const { data, error } = await supabase.rpc('get_user_stripe_stats')

      if (error) {
        throw error
      }

      // RPC returns array, get first item
      const stats = data && data.length > 0 ? data[0] : null
      setUserStats(stats)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch user stats'
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

  // Fetch all analytics data
  const fetchAllAnalytics = useCallback(async () => {
    setLoading(true)
    
    try {
      await Promise.all([
        fetchUserStats(),
        fetchPackageAnalytics(),
        fetchDailyRevenue(30),
        fetchMonthlyRevenue(12)
      ])
    } catch (err) {
      // Individual errors are handled in each function
      console.error('Error fetching analytics:', err)
    } finally {
      setLoading(false)
    }
  }, [fetchUserStats, fetchPackageAnalytics, fetchDailyRevenue, fetchMonthlyRevenue])

  return {
    // State
    dailyRevenue,
    monthlyRevenue,
    packageAnalytics,
    userStats,
    loading,
    error,
    
    // Actions
    fetchDailyRevenue,
    fetchMonthlyRevenue,
    fetchPackageAnalytics,
    fetchUserStats,
    fetchAllAnalytics,
    
    // Utilities
    formatCurrency: (cents: number) => {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
      }).format(cents / 100)
    },
    
    formatDate: (dateString: string) => {
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }).format(new Date(dateString))
    },
    
    formatMonth: (dateString: string) => {
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'long'
      }).format(new Date(dateString))
    }
  }
}