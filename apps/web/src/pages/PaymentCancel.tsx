/**
 * Payment Cancel Page
 * Displayed when user cancels Stripe Checkout
 */

import React from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { XCircle, ArrowLeft, CreditCard, HelpCircle } from 'lucide-react'

const PaymentCancel: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-red-50 p-4">
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 p-3 rounded-full bg-orange-100">
            <XCircle className="h-8 w-8 text-orange-600" />
          </div>
          <CardTitle className="text-2xl text-orange-600">
            Payment Cancelled
          </CardTitle>
          <CardDescription>
            Your payment was cancelled. No charges were made to your account.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-6">
          <Alert>
            <HelpCircle className="h-4 w-4" />
            <AlertDescription>
              Your payment session was cancelled and no tokens were purchased. 
              You can try again at any time.
            </AlertDescription>
          </Alert>

          {/* Common Reasons */}
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900">Common Reasons for Cancellation</h3>
            <ul className="space-y-2 text-sm text-gray-600">
              <li className="flex items-start gap-2">
                <span className="text-orange-500">•</span>
                You clicked the "back" button during checkout
              </li>
              <li className="flex items-start gap-2">
                <span className="text-orange-500">•</span>
                You closed the browser tab or window
              </li>
              <li className="flex items-start gap-2">
                <span className="text-orange-500">•</span>
                You decided to choose a different package
              </li>
              <li className="flex items-start gap-2">
                <span className="text-orange-500">•</span>
                You encountered an issue with payment information
              </li>
            </ul>
          </div>

          {/* What You Can Do */}
          <div className="space-y-3">
            <h3 className="font-semibold text-gray-900">What You Can Do</h3>
            <div className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg">
                <CreditCard className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-blue-900">Try Again</h4>
                  <p className="text-sm text-blue-700">
                    Return to the token packages and complete your purchase
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-3 p-3 bg-green-50 rounded-lg">
                <HelpCircle className="h-5 w-5 text-green-600 mt-0.5" />
                <div>
                  <h4 className="font-medium text-green-900">Need Help?</h4>
                  <p className="text-sm text-green-700">
                    Contact our support team if you're experiencing issues
                  </p>
                </div>
              </div>
            </div>
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
              <Link to="/purchase-tokens">
                <CreditCard className="w-4 h-4 mr-2" />
                Try Again
              </Link>
            </Button>
          </div>

          {/* Support Contact */}
          <div className="text-center text-sm text-gray-500 pt-4 border-t">
            <p>Having trouble? Contact us at</p>
            <a href="mailto:support@aionvideos.com" className="text-blue-600 hover:underline">
              support@aionvideos.com
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default PaymentCancel