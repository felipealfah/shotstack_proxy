import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'
import { generateApiKey, hashApiKey } from '@/utils'
import { z } from 'zod'

const createApiKeySchema = z.object({
  name: z.string().min(1, 'Name is required').max(50, 'Name must be less than 50 characters'),
  description: z.string().optional()
})

export async function GET() {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { data: apiKeys, error } = await supabase
      .from('api_keys')
      .select('id, name, description, key_hash, is_active, created_at, last_used_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      console.error('Error fetching API keys:', error)
      return NextResponse.json({ error: 'Failed to fetch API keys' }, { status: 500 })
    }

    return NextResponse.json({ apiKeys })
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validatedData = createApiKeySchema.parse(body)

    // Check if user has reached the maximum number of API keys (10)
    const { count, error: countError } = await supabase
      .from('api_keys')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)
      .eq('is_active', true)

    if (countError) {
      console.error('Error checking API key count:', countError)
      return NextResponse.json({ error: 'Failed to check API key limit' }, { status: 500 })
    }

    if (count && count >= 10) {
      return NextResponse.json({ 
        error: 'Maximum number of API keys reached (10)' 
      }, { status: 400 })
    }

    // Generate new API key
    const apiKey = generateApiKey()
    const keyHash = await hashApiKey(apiKey)

    // Store the API key in the database
    const { data: newApiKey, error: insertError } = await supabase
      .from('api_keys')
      .insert({
        user_id: user.id,
        name: validatedData.name,
        description: validatedData.description,
        key_hash: keyHash,
        is_active: true
      })
      .select('id, name, description, key_hash, is_active, created_at, last_used_at')
      .single()

    if (insertError) {
      console.error('Error creating API key:', insertError)
      return NextResponse.json({ error: 'Failed to create API key' }, { status: 500 })
    }

    // Return the API key (only show it once)
    return NextResponse.json({
      apiKey: {
        ...newApiKey,
        key: apiKey // Only returned on creation
      }
    }, { status: 201 })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ 
        error: 'Validation error',
        details: error.errors 
      }, { status: 400 })
    }
    
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}