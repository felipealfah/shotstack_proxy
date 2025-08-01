'use client'

import { useState, useEffect } from 'react'
import { ApiKeyListResponse, CreateApiKeyRequest, CreateApiKeyResponse } from '@/types/api'

export function useApiKeys() {
  const [keys, setKeys] = useState<ApiKeyListResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchKeys = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/api-keys')
      
      if (!response.ok) {
        throw new Error('Failed to fetch API keys')
      }
      
      const data = await response.json()
      setKeys(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const createKey = async (request: CreateApiKeyRequest): Promise<CreateApiKeyResponse> => {
    const response = await fetch('/api/api-keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to create API key')
    }

    const newKey = await response.json()
    await fetchKeys() // Refresh the list
    return newKey
  }

  const updateKey = async (id: string, updates: { name?: string; is_active?: boolean }) => {
    const response = await fetch(`/api/api-keys/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to update API key')
    }

    await fetchKeys() // Refresh the list
  }

  const deleteKey = async (id: string) => {
    const response = await fetch(`/api/api-keys/${id}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to delete API key')
    }

    await fetchKeys() // Refresh the list
  }

  useEffect(() => {
    fetchKeys()
  }, [])

  return {
    keys,
    loading,
    error,
    createKey,
    updateKey,
    deleteKey,
    refresh: fetchKeys
  }
}