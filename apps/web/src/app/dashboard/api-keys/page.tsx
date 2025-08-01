'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Link from 'next/link'

interface ApiKey {
  id: string
  name: string
  description?: string
  key_hash: string
  is_active: boolean
  created_at: string
  last_used_at?: string
}

export default function ApiKeysPage() {
  const { user, loading } = useAuth()
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [loadingKeys, setLoadingKeys] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [newApiKey, setNewApiKey] = useState({ name: '', description: '' })
  const [createdApiKey, setCreatedApiKey] = useState<{ key: string } | null>(null)

  useEffect(() => {
    if (user) {
      fetchApiKeys()
    }
  }, [user])

  const fetchApiKeys = async () => {
    try {
      const response = await fetch('/api/api-keys')
      if (response.ok) {
        const data = await response.json()
        setApiKeys(data.apiKeys || [])
      } else {
        setError('Failed to fetch API keys')
      }
    } catch (err) {
      setError('An error occurred while fetching API keys')
    } finally {
      setLoadingKeys(false)
    }
  }

  const createApiKey = async () => {
    if (!newApiKey.name.trim()) {
      setError('API key name is required')
      return
    }

    setIsCreating(true)
    setError('')

    try {
      const response = await fetch('/api/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newApiKey)
      })

      const data = await response.json()

      if (response.ok) {
        setCreatedApiKey({ key: data.apiKey.key })
        setSuccess('API key created successfully!')
        setNewApiKey({ name: '', description: '' })
        fetchApiKeys() // Refresh the list
      } else {
        setError(data.error || 'Failed to create API key')
      }
    } catch (err) {
      setError('An error occurred while creating the API key')
    } finally {
      setIsCreating(false)
    }
  }

  const toggleApiKey = async (id: string, isActive: boolean) => {
    try {
      const response = await fetch(`/api/api-keys/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !isActive })
      })

      if (response.ok) {
        setSuccess('API key updated successfully!')
        fetchApiKeys()
      } else {
        setError('Failed to update API key')
      }
    } catch (err) {
      setError('An error occurred while updating the API key')
    }
  }

  if (loading || loadingKeys) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-gray-900"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">API Keys</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage your API keys for accessing the video rendering service
              </p>
            </div>
            <Link href="/dashboard">
              <Button variant="outline">← Back to Dashboard</Button>
            </Link>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-6">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-6">
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {createdApiKey && (
            <Alert className="mb-6">
              <AlertDescription>
                <strong>🔑 Your new API key (save this, it won&apos;t be shown again!):</strong>
                <div className="mt-2 p-2 bg-gray-100 rounded font-mono text-sm break-all">
                  {createdApiKey.key}
                </div>
              </AlertDescription>
            </Alert>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Create API Key Form */}
            <Card>
              <CardHeader>
                <CardTitle>Create New API Key</CardTitle>
                <CardDescription>
                  Generate a new API key to authenticate your requests
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="name">Name *</Label>
                  <Input
                    id="name"
                    placeholder="e.g., Production Key"
                    value={newApiKey.name}
                    onChange={(e) => setNewApiKey({ ...newApiKey, name: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    placeholder="Optional description"
                    value={newApiKey.description}
                    onChange={(e) => setNewApiKey({ ...newApiKey, description: e.target.value })}
                  />
                </div>
                <Button 
                  onClick={createApiKey} 
                  disabled={isCreating}
                  className="w-full"
                >
                  {isCreating ? 'Creating...' : 'Create API Key'}
                </Button>
              </CardContent>
            </Card>

            {/* API Keys List */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>Your API Keys ({apiKeys.length}/10)</CardTitle>
                  <CardDescription>
                    You can have up to 10 active API keys
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {apiKeys.length === 0 ? (
                    <p className="text-gray-500 text-center py-8">
                      No API keys found. Create your first API key to get started.
                    </p>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Created</TableHead>
                          <TableHead>Last Used</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {apiKeys.map((key) => (
                          <TableRow key={key.id}>
                            <TableCell>
                              <div>
                                <p className="font-medium">{key.name}</p>
                                {key.description && (
                                  <p className="text-sm text-gray-500">{key.description}</p>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant={key.is_active ? "default" : "secondary"}>
                                {key.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              {new Date(key.created_at).toLocaleDateString()}
                            </TableCell>
                            <TableCell>
                              {key.last_used_at 
                                ? new Date(key.last_used_at).toLocaleDateString()
                                : 'Never'
                              }
                            </TableCell>
                            <TableCell>
                              <Button
                                size="sm"
                                variant={key.is_active ? "destructive" : "default"}
                                onClick={() => toggleApiKey(key.id, key.is_active)}
                              >
                                {key.is_active ? 'Deactivate' : 'Activate'}
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Usage Instructions */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>How to Use Your API Key</CardTitle>
              <CardDescription>
                Instructions for using your API key with the Shotstack Intermediary API
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium">1. Base URL</h4>
                  <p className="text-sm text-gray-600">
                    Use this base URL for all API requests:
                  </p>
                  <code className="block mt-1 p-2 bg-gray-100 rounded text-sm">
                    http://localhost:8001/api/v1
                  </code>
                </div>
                
                <div>
                  <h4 className="font-medium">2. Authentication</h4>
                  <p className="text-sm text-gray-600">
                    Include your API key in the Authorization header:
                  </p>
                  <code className="block mt-1 p-2 bg-gray-100 rounded text-sm">
                    Authorization: Bearer your_api_key_here
                  </code>
                </div>

                <div>
                  <h4 className="font-medium">3. Example Request</h4>
                  <pre className="mt-1 p-2 bg-gray-100 rounded text-sm overflow-x-auto">
{`curl -X POST http://localhost:8001/api/v1/render \\
  -H "Authorization: Bearer your_api_key_here" \\
  -H "Content-Type: application/json" \\
  -d '{
    "timeline": {
      "tracks": [{
        "clips": [{
          "asset": {
            "type": "video",
            "src": "https://example.com/video.mp4"
          },
          "start": 0,
          "length": 5
        }]
      }]
    },
    "output": {
      "format": "mp4",
      "resolution": "sd"
    }
  }'`}
                  </pre>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}