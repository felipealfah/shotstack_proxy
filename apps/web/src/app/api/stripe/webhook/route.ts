import { NextRequest, NextResponse } from 'next/server'
// import { headers } from 'next/headers'
// import Stripe from 'stripe'
// import { createServiceClient } from '@/utils/supabase-server'

// TODO: Reabilitar integração Stripe posteriormente
// const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
//   apiVersion: '2025-02-24.acacia',
// })
// const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET!

export async function POST(request: NextRequest) {
  try {
    // TODO: Integração Stripe temporáriamente desabilitada para primeiro teste
    return NextResponse.json({ 
      error: 'Stripe webhook temporarily disabled - under development',
      message: 'Payment processing will be implemented in next phase'
    }, { status: 501 })
    
    /*
    // Código Stripe será reativado posteriormente
    const body = await request.text()
    const headersList = headers()
    const sig = headersList.get('stripe-signature')!

    let event: Stripe.Event

    try {
      event = stripe.webhooks.constructEvent(body, sig, endpointSecret)
    } catch (err) {
      console.error('Webhook signature verification failed:', err)
      return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
    }

    const supabase = createServiceClient()

    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session
        // Handle successful payment
        break
      }
      default:
        console.log(`Unhandled event type ${event.type}`)
    }

    return NextResponse.json({ received: true })
    */
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}