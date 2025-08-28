/**
 * Token Purchase Component
 * Displays available token packages and handles Stripe checkout
 */

import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useStripe, TokenPackage } from '@/hooks/useStripe'
import { Zap, CreditCard, CheckCircle, AlertCircle } from 'lucide-react'

const TokenPurchase: React.FC = () => {
  const { packages, loading, error, fetchPackages, createCheckoutSession } = useStripe()
  const [purchasingPackage, setPurchasingPackage] = useState<string | null>(null)

  useEffect(() => {
    fetchPackages()
  }, [fetchPackages])

  const handlePurchase = async (packageType: string) => {
    setPurchasingPackage(packageType)
    try {
      await createCheckoutSession(packageType)
    } catch (err) {
      console.error('Purchase failed:', err)
    } finally {
      setPurchasingPackage(null)
    }
  }

  const formatPrice = (cents: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(cents / 100)
  }

  const getPricePerToken = (pkg: TokenPackage) => {
    return (pkg.amount_cents / pkg.tokens / 100).toFixed(3)
  }

  const getSavingsPercentage = (pkg: TokenPackage) => {
    // Calculate savings compared to starter package
    const starterPackage = packages.find(p => p.type === 'starter')
    if (!starterPackage || pkg.type === 'starter') return 0
    
    const starterPricePerToken = starterPackage.amount_cents / starterPackage.tokens
    const currentPricePerToken = pkg.amount_cents / pkg.tokens
    const savings = ((starterPricePerToken - currentPricePerToken) / starterPricePerToken) * 100
    
    return Math.round(savings)
  }

  if (loading && packages.length === 0) {
    return (
      <div className="space-y-4">
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold mb-2">Purchase Video Tokens</h2>
          <p className="text-muted-foreground">Choose a token package to start creating videos</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="relative">
              <CardHeader>
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-4 w-full" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-12 w-full mb-4" />
                <Skeleton className="h-4 w-full mb-2" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-full" />
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load token packages. Please try refreshing the page.
          <br />
          <small className="opacity-75">Error: {error}</small>
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-bold mb-2 flex items-center justify-center gap-2">
          <Zap className="text-yellow-500" />
          Purchase Video Tokens
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Each token equals approximately 1 minute of high-quality video rendering. 
          Choose the package that best fits your needs.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {packages.map((pkg) => {
          const savings = getSavingsPercentage(pkg)
          const isPopular = pkg.recommended
          const isPurchasing = purchasingPackage === pkg.type
          
          return (
            <Card 
              key={pkg.type} 
              className={`relative transition-all duration-200 hover:shadow-lg ${
                isPopular ? 'ring-2 ring-primary border-primary' : ''
              }`}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground">
                    Most Popular
                  </Badge>
                </div>
              )}
              
              {savings > 0 && (
                <div className="absolute -top-3 right-4">
                  <Badge variant="secondary" className="bg-green-100 text-green-700">
                    Save {savings}%
                  </Badge>
                </div>
              )}

              <CardHeader className="text-center">
                <CardTitle className="capitalize text-xl">
                  {pkg.type}
                </CardTitle>
                <CardDescription className="text-sm">
                  {pkg.description}
                </CardDescription>
                <div className="space-y-1">
                  <div className="text-3xl font-bold">
                    {formatPrice(pkg.amount_cents)}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    ${getPricePerToken(pkg)} per token
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="flex items-center justify-center gap-2 p-3 bg-secondary rounded-lg">
                  <Zap className="h-5 w-5 text-yellow-500" />
                  <span className="text-lg font-semibold">{pkg.tokens} tokens</span>
                </div>
                
                <div className="text-sm text-muted-foreground text-center">
                  ≈ {pkg.tokens} minutes of video
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>High-quality rendering</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>Google Cloud Storage</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="h-4 w-4 text-green-500" />
                    <span>API access included</span>
                  </div>
                </div>
              </CardContent>

              <CardFooter>
                <Button 
                  className="w-full" 
                  onClick={() => handlePurchase(pkg.type)}
                  disabled={isPurchasing || loading}
                  variant={isPopular ? "default" : "outline"}
                >
                  {isPurchasing ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4 mr-2" />
                      Purchase Now
                    </>
                  )}
                </Button>
              </CardFooter>
            </Card>
          )
        })}
      </div>

      <div className="text-center text-sm text-muted-foreground space-y-2">
        <p>
          🔒 Secure payments powered by Stripe • 💳 All major credit cards accepted
        </p>
        <p>
          ⚡ Tokens are added instantly after successful payment • 📊 View your purchase history in the dashboard
        </p>
      </div>
    </div>
  )
}

export default TokenPurchase