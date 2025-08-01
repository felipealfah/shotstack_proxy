import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'
import { z } from 'zod'

const updateApiKeySchema = z.object({
  name: z.string().min(1, 'Name is required').max(50, 'Name must be less than 50 characters').optional(),
  description: z.string().optional(),
  is_active: z.boolean().optional()
})

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const validatedData = updateApiKeySchema.parse(body)

    // Check if the API key belongs to the user
    const { data: existingApiKey, error: fetchError } = await supabase
      .from('api_keys')
      .select('*')
      .eq('id', id)
      .eq('user_id', user.id)
      .single()

    if (fetchError || !existingApiKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 404 })
    }

    // Update the API key
    const { data: updatedApiKey, error: updateError } = await supabase
      .from('api_keys')
      .update(validatedData)
      .eq('id', id)
      .eq('user_id', user.id)
      .select('id, name, description, key_hash, is_active, created_at, last_used_at')
      .single()

    if (updateError) {
      console.error('Error updating API key:', updateError)
      return NextResponse.json({ error: 'Failed to update API key' }, { status: 500 })
    }

    return NextResponse.json({ apiKey: updatedApiKey })
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

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Check if the API key belongs to the user
    const { data: existingApiKey, error: fetchError } = await supabase
      .from('api_keys')
      .select('*')
      .eq('id', id)
      .eq('user_id', user.id)
      .single()

    if (fetchError || !existingApiKey) {
      return NextResponse.json({ error: 'API key not found' }, { status: 404 })
    }

    // Soft delete by setting is_active to false
    const { error: deleteError } = await supabase
      .from('api_keys')
      .update({ is_active: false })
      .eq('id', id)
      .eq('user_id', user.id)

    if (deleteError) {
      console.error('Error deleting API key:', deleteError)
      return NextResponse.json({ error: 'Failed to delete API key' }, { status: 500 })
    }

    return NextResponse.json({ message: 'API key deleted successfully' })
  } catch (error) {
    console.error('Unexpected error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}