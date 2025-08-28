/**
 * Payment Success Page
 * Displayed after successful Stripe Checkout completion
 */

import React, { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { useStripe } from '@/hooks/useStripe'
import { CheckCircle, ArrowLeft, ExternalLink, Zap } from 'lucide-react'

const PaymentSuccess: React.FC = () => {
  const [searchParams] = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const { getSessionStatus } = useStripe()
  
  const [sessionData, setSessionData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSessionData = async () => {
      if (!sessionId) {
        setError('No session ID found in URL')
        setLoading(false)
        return
      }

      try {
        const data = await getSessionStatus(sessionId)
        if (data) {
          setSessionData(data)
        } else {
          setError('Failed to retrieve payment information')
        }
      } catch (err) {
        setError('Error fetching payment information')
        console.error('Session fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchSessionData()
  }, [sessionId, getSessionStatus])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-blue-50">
        <Card className="w-full max-w-lg mx-4">
          <CardHeader className="text-center">
            <Skeleton className="h-12 w-12 rounded-full mx-auto mb-4" />
            <Skeleton className="h-8 w-3/4 mx-auto mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-2/3 mx-auto" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !sessionData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50">
        <Card className="w-full max-w-lg mx-4">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 p-3 rounded-full bg-red-100">
              <CheckCircle className="h-8 w-8 text-red-600" />
            </div>
            <CardTitle className="text-2xl text-red-600">
              Payment Information Error
            </CardTitle>
            <CardDescription>
              We couldn't retrieve your payment information.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert variant="destructive">
              <AlertDescription>
                {error || 'Unknown error occurred'}
              </AlertDescription>
            </Alert>
            <div className="flex gap-3">
              <Button asChild variant="outline" className="flex-1">
                <Link to="/">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Go Home
                </Link>
              </Button>
              <Button asChild className="flex-1">
                <Link to="/dashboard">
                  Go to Dashboard
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  const formatPrice = (cents: number | undefined) => {
    if (!cents) return 'N/A'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100)
  }

  const isPaid = sessionData.payment_status === 'paid'

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-blue-50 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 p-3 rounded-full bg-green-100">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <CardTitle className="text-2xl text-green-600">
            {isPaid ? 'Payment Successful!' : 'Payment Processing'}
          </CardTitle>
          <CardDescription>
            {isPaid 
              ? 'Your tokens have been added to your account.'
              : 'Your payment is being processed. Tokens will be added shortly.'
            }
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Payment Details */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <h3 className="font-semibold text-gray-900 mb-3">Payment Details</h3>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Amount Paid:</span>
              <span className="font-semibold">{formatPrice(sessionData.amount_total)}</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Payment Status:</span>
              <span className={`font-semibold capitalize ${
                isPaid ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {sessionData.payment_status}
              </span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-gray-600">Session ID:</span>
              <span className="text-sm text-gray-500 font-mono">{sessionId?.slice(-8)}</span>
            </div>

            {sessionData.customer_email && (
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Email:</span>
                <span className="text-sm">{sessionData.customer_email}</span>
              </div>
            )}
          </div>

          {/* Next Steps */}
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900">What's Next?</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-500" />
                Your tokens are now available in your account
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                You can start creating videos immediately
              </li>
              <li className="flex items-center gap-2">
                <ExternalLink className="h-4 w-4 text-blue-500" />
                Access your API keys and documentation in the dashboard
              </li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4">
            <Button asChild variant="outline" className="flex-1">
              <Link to="/">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Home
              </Link>
            </Button>
            <Button asChild className="flex-1">
              <Link to="/dashboard">
                View Dashboard
              </Link>
            </Button>
          </div>

          {/* Receipt Note */}
          <div className="text-center text-sm text-gray-500 pt-4 border-t">
            <p>A receipt has been sent to your email address.</p>
            <p>Keep this for your records.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default PaymentSuccess