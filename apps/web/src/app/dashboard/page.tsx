'use client'

import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const { user, loading, signOut } = useAuth()
  const router = useRouter()

  const handleSignOut = async () => {
    const { error } = await signOut()
    if (!error) {
      router.push('/')
    }
  }

  if (loading) {
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
            <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, {user?.email}
              </span>
              <Button variant="outline" onClick={handleSignOut}>
                Sign out
              </Button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>API Keys</CardTitle>
                <CardDescription>
                  Manage your API keys for accessing the video rendering service
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-4">
                  Create and manage API keys to authenticate your requests
                </p>
                <Button>Manage API Keys</Button>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Tokens</CardTitle>
                <CardDescription>
                  View your token balance and purchase more tokens
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-4">
                  Tokens are used to pay for video rendering requests
                </p>
                <Button>View Tokens</Button>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Usage</CardTitle>
                <CardDescription>
                  Monitor your API usage and rendering statistics
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600 mb-4">
                  Track your video rendering requests and token consumption
                </p>
                <Button>View Usage</Button>
              </CardContent>
            </Card>
          </div>
          
          <div className="mt-8">
            <Card>
              <CardHeader>
                <CardTitle>Getting Started</CardTitle>
                <CardDescription>
                  Quick steps to start using the Shotstack Intermediary Platform
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ol className="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Purchase tokens to pay for video rendering requests</li>
                  <li>Create an API key to authenticate your requests</li>
                  <li>Use your API key to make requests to our intermediary service</li>
                  <li>Monitor your usage and token consumption in the dashboard</li>
                </ol>
                <div className="mt-4">
                  <Button variant="outline" className="mr-2">
                    View Documentation
                  </Button>
                  <Button variant="outline">
                    API Reference
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}