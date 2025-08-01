import { createServerSupabaseClient } from '@/utils/supabase-server'
import { NextRequest, NextResponse } from 'next/server'

export async function GET(request: NextRequest) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/dashboard'

  if (code) {
    const supabase = createServerSupabaseClient()
    
    const { data, error } = await supabase.auth.exchangeCodeForSession(code)
    
    if (!error && data.user) {
      // Create user record if it doesn't exist
      const { error: upsertError } = await supabase
        .from('users')
        .upsert({
          id: data.user.id,
          email: data.user.email,
          token_balance: 0,
          created_at: new Date().toISOString()
        }, {
          onConflict: 'id',
          ignoreDuplicates: true
        })

      if (upsertError) {
        console.error('Error creating user record:', upsertError)
      }

      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  // Return the user to an error page with instructions
  return NextResponse.redirect(`${origin}/auth/login?error=oauth_error`)
}