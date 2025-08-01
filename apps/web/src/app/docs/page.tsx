'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'

const SwaggerUI = dynamic(() => import('swagger-ui-react'), { 
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-64">Loading API Documentation...</div>
})

export default function ApiDocsPage() {
  const [spec, setSpec] = useState(null)

  useEffect(() => {
    fetch('/api/swagger')
      .then(res => res.json())
      .then(data => setSpec(data))
      .catch(err => console.error('Failed to load API spec:', err))
  }, [])

  if (!spec) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading API Documentation...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      <div className="bg-gray-50 border-b">
        <div className="container mx-auto py-6 px-4">
          <h1 className="text-3xl font-bold text-gray-900">
            API Documentation
          </h1>
          <p className="text-gray-600 mt-2">
            Interactive documentation for the Shotstack Intermediary Platform API
          </p>
        </div>
      </div>
      
      <div className="container mx-auto px-4 py-8">
        <SwaggerUI 
          spec={spec}
          docExpansion="list"
          defaultModelsExpandDepth={2}
          defaultModelExpandDepth={2}
          tryItOutEnabled={true}
          persistAuthorization={true}
          displayRequestDuration={true}
          filter={true}
          showExtensions={true}
          showCommonExtensions={true}
        />
      </div>
    </div>
  )
}