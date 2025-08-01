'use client'

import { useState, useEffect } from 'react'
import { UsageStatsResponse, UsageLog, UsageStatsQuery } from '@/types/api'

export function useUsage(query?: UsageStatsQuery) {
  const [stats, setStats] = useState<UsageStatsResponse | null>(null)
  const [logs, setLogs] = useState<UsageLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = async () => {
    try {
      setLoading(true)
      const params = new URLSearchParams()
      
      if (query?.start_date) params.append('start_date', query.start_date)
      if (query?.end_date) params.append('end_date', query.end_date)
      if (query?.limit) params.append('limit', query.limit.toString())

      const response = await fetch(`/api/usage/stats?${params}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch usage stats')
      }
      
      const data = await response.json()
      setStats(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchLogs = async () => {
    try {
      const params = new URLSearchParams()
      
      if (query?.start_date) params.append('start_date', query.start_date)
      if (query?.end_date) params.append('end_date', query.end_date)
      if (query?.limit) params.append('limit', query.limit.toString())

      const response = await fetch(`/api/usage/logs?${params}`)
      
      if (!response.ok) {
        throw new Error('Failed to fetch usage logs')
      }
      
      const data = await response.json()
      setLogs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    }
  }

  useEffect(() => {
    fetchStats()
    fetchLogs()
  }, [query])

  return {
    stats,
    logs,
    loading,
    error,
    refresh: () => {
      fetchStats()
      fetchLogs()
    }
  }
}