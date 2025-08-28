/**
 * Transaction History Component
 * Displays user's Stripe payment transaction history
 */

import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useStripe, TransactionHistory } from '@/hooks/useStripe'
import { 
  Receipt, 
  CreditCard, 
  CheckCircle, 
  Clock, 
  XCircle, 
  RefreshCw,
  DollarSign,
  Zap,
  Calendar,
  AlertCircle
} from 'lucide-react'

const TransactionHistory: React.FC = () => {
  const { transactions, loading, error, fetchTransactionHistory } = useStripe()
  const [totalStats, setTotalStats] = useState({
    total_spent_usd: 0,
    total_tokens_purchased: 0,
    total_transactions: 0
  })

  useEffect(() => {
    const loadTransactions = async () => {
      const data = await fetchTransactionHistory(50, 0) // Load up to 50 transactions
      if (data) {
        setTotalStats({
          total_spent_usd: data.total_spent_usd,
          total_tokens_purchased: data.total_tokens_purchased,
          total_transactions: data.total_transactions
        })
      }
    }

    loadTransactions()
  }, [fetchTransactionHistory])

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'pending':
        return <Clock className="h-4 w-4 text-yellow-500" />
      case 'failed':
      case 'cancelled':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'failed':
      case 'cancelled':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatPrice = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100)
  }

  const formatDate = (dateString: string) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(dateString))
  }

  if (loading && transactions.length === 0) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Skeleton className="h-6 w-6" />
              <Skeleton className="h-6 w-40" />
            </div>
            <Skeleton className="h-4 w-60" />
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-8 w-16" />
                </div>
              ))}
            </div>
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <Skeleton className="h-8 w-8 rounded" />
                    <div className="space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Receipt className="h-5 w-5 text-blue-600" />
              Transaction History
            </CardTitle>
            <CardDescription>
              Your token purchase history and payment records
            </CardDescription>
          </div>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => fetchTransactionHistory()}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Failed to load transaction history: {error}
            </AlertDescription>
          </Alert>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-blue-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 text-blue-600 mb-1">
              <DollarSign className="h-4 w-4" />
              <span className="text-sm font-medium">Total Spent</span>
            </div>
            <div className="text-2xl font-bold text-blue-900">
              ${totalStats.total_spent_usd.toFixed(2)}
            </div>
          </div>

          <div className="bg-yellow-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 text-yellow-600 mb-1">
              <Zap className="h-4 w-4" />
              <span className="text-sm font-medium">Tokens Purchased</span>
            </div>
            <div className="text-2xl font-bold text-yellow-900">
              {totalStats.total_tokens_purchased.toLocaleString()}
            </div>
          </div>

          <div className="bg-green-50 p-4 rounded-lg">
            <div className="flex items-center gap-2 text-green-600 mb-1">
              <Receipt className="h-4 w-4" />
              <span className="text-sm font-medium">Total Purchases</span>
            </div>
            <div className="text-2xl font-bold text-green-900">
              {totalStats.total_transactions}
            </div>
          </div>
        </div>

        {/* Transactions List */}
        <div className="space-y-3">
          {transactions.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium mb-2">No transactions yet</h3>
              <p className="text-sm">Your token purchases will appear here.</p>
            </div>
          ) : (
            transactions.map((transaction) => (
              <div 
                key={transaction.id} 
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <CreditCard className="h-5 w-5 text-blue-600" />
                  </div>
                  
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium capitalize">
                        {transaction.package_type} Package
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {transaction.tokens_purchased} tokens
                      </Badge>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(transaction.created_at)}
                      </div>
                      
                      {transaction.completed_at && (
                        <span>• Completed {formatDate(transaction.completed_at)}</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="font-semibold">
                      {formatPrice(transaction.amount_cents)}
                    </div>
                    <div className="text-sm text-gray-500">
                      ${(transaction.amount_cents / transaction.tokens_purchased / 100).toFixed(3)}/token
                    </div>
                  </div>
                  
                  <Badge className={getStatusColor(transaction.status)}>
                    <div className="flex items-center gap-1">
                      {getStatusIcon(transaction.status)}
                      <span className="capitalize">{transaction.status}</span>
                    </div>
                  </Badge>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Load More Button (if needed) */}
        {transactions.length > 0 && transactions.length < totalStats.total_transactions && (
          <div className="text-center pt-4">
            <Button 
              variant="outline" 
              onClick={() => fetchTransactionHistory(transactions.length + 20)}
              disabled={loading}
            >
              Load More Transactions
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default TransactionHistory