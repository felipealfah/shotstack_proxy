import { NextRequest, NextResponse } from 'next/server'
// import { createServerSupabaseClient } from '@/utils/supabase-server'
// import Stripe from 'stripe'
import { z } from 'zod'

// TODO: Reabilitar integração Stripe posteriormente
// const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
//   apiVersion: '2025-02-24.acacia',
// })

const createCheckoutSchema = z.object({
  tokens: z.number().min(100, 'Minimum purchase is 100 tokens').max(10000, 'Maximum purchase is 10,000 tokens'),
  successUrl: z.string().url().optional(),
  cancelUrl: z.string().url().optional()
})

// Token pricing: $0.01 per token (1 cent per minute of video)
const TOKEN_PRICE_CENTS = 1

export async function POST(request: NextRequest) {
  try {
    // TODO: Integração Stripe temporáriamente desabilitada para primeiro teste
    return NextResponse.json({ 
      error: 'Stripe integration temporarily disabled - under development',
      message: 'Token purchase will be implemented in next phase'
    }, { status: 501 })
    
    /*
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validatedData = createCheckoutSchema.parse(body)

    const { tokens, successUrl, cancelUrl } = validatedData
    const totalAmountCents = tokens * TOKEN_PRICE_CENTS

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: `${tokens} Video Rendering Tokens`,
              description: `Purchase ${tokens} tokens for video rendering (1 token = 1 minute of video)`,
            },
            unit_amount: totalAmountCents,
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: successUrl || `${process.env.NEXT_PUBLIC_BASE_URL}/dashboard?success=true`,
      cancel_url: cancelUrl || `${process.env.NEXT_PUBLIC_BASE_URL}/dashboard?canceled=true`,
      metadata: {
        user_id: user.id,
        tokens_amount: tokens.toString(),
      },
      customer_email: user.email,
      billing_address_collection: 'required',
      allow_promotion_codes: true,
    })

    return NextResponse.json({
      sessionId: session.id,
      url: session.url
    })
    */
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}