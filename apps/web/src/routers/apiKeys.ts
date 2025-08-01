import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'
import { handleApiError, errors } from '@/functions/error_handling'
import { createApiKeySchema, updateApiKeySchema } from '@/utils/validations'
import { generateApiKey, hashApiKey } from '@/utils'

/**
 * @swagger
 * /api/api-keys:
 *   get:
 *     summary: List user's API keys
 *     tags:
 *       - API Keys
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: List of API keys
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 type: object
 *                 properties:
 *                   id:
 *                     type: string
 *                   name:
 *                     type: string
 *                   created_at:
 *                     type: string
 *                   last_used:
 *                     type: string
 *                     nullable: true
 *                   is_active:
 *                     type: boolean
 *       401:
 *         description: Unauthorized
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleGetApiKeys() {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      throw errors.unauthorized()
    }

    const { data: keys, error } = await supabase
      .from('api_keys')
      .select('id, name, created_at, last_used, is_active')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      throw error
    }

    return NextResponse.json(keys || [])
  } catch (error) {
    return handleApiError(error)
  }
}

/**
 * @swagger
 * /api/api-keys:
 *   post:
 *     summary: Create a new API key
 *     tags:
 *       - API Keys
 *     security:
 *       - BearerAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - name
 *             properties:
 *               name:
 *                 type: string
 *                 maxLength: 50
 *     responses:
 *       201:
 *         description: API key created successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 id:
 *                   type: string
 *                 name:
 *                   type: string
 *                 key:
 *                   type: string
 *                   description: The actual API key (only returned once)
 *                 created_at:
 *                   type: string
 *       400:
 *         description: Bad request
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleCreateApiKey(request: NextRequest) {
  try {
    const body = await request.json()
    const { name } = createApiKeySchema.parse(body)

    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      throw errors.unauthorized()
    }

    // Generate API key
    const apiKey = generateApiKey()
    const keyHash = await hashApiKey(apiKey)

    // Save to database
    const { data, error } = await supabase
      .from('api_keys')
      .insert({
        user_id: user.id,
        name,
        key_hash: keyHash
      })
      .select('id, name, created_at')
      .single()

    if (error) {
      throw error
    }

    return NextResponse.json(
      {
        ...data,
        key: apiKey // Only returned once
      },
      { status: 201 }
    )
  } catch (error) {
    return handleApiError(error)
  }
}

/**
 * @swagger
 * /api/api-keys/{id}:
 *   put:
 *     summary: Update an API key
 *     tags:
 *       - API Keys
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: string
 *           format: uuid
 *     requestBody:
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             properties:
 *               name:
 *                 type: string
 *               is_active:
 *                 type: boolean
 *     responses:
 *       200:
 *         description: API key updated successfully
 *       404:
 *         description: API key not found
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleUpdateApiKey(request: NextRequest, keyId: string) {
  try {
    const body = await request.json()
    const updates = updateApiKeySchema.parse(body)

    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      throw errors.unauthorized()
    }

    const { data, error } = await supabase
      .from('api_keys')
      .update(updates)
      .eq('id', keyId)
      .eq('user_id', user.id)
      .select()
      .single()

    if (error) {
      throw error
    }

    if (!data) {
      throw errors.notFound('API key')
    }

    return NextResponse.json({
      message: 'API key updated successfully'
    })
  } catch (error) {
    return handleApiError(error)
  }
}

/**
 * @swagger
 * /api/api-keys/{id}:
 *   delete:
 *     summary: Delete an API key
 *     tags:
 *       - API Keys
 *     security:
 *       - BearerAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: string
 *           format: uuid
 *     responses:
 *       200:
 *         description: API key deleted successfully
 *       404:
 *         description: API key not found
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleDeleteApiKey(request: NextRequest, keyId: string) {
  try {
    const supabase = createServerSupabaseClient()
    
    const { data: { user }, error: authError } = await supabase.auth.getUser()
    if (authError || !user) {
      throw errors.unauthorized()
    }

    const { data, error } = await supabase
      .from('api_keys')
      .delete()
      .eq('id', keyId)
      .eq('user_id', user.id)
      .select()
      .single()

    if (error) {
      throw error
    }

    if (!data) {
      throw errors.notFound('API key')
    }

    return NextResponse.json({
      message: 'API key deleted successfully'
    })
  } catch (error) {
    return handleApiError(error)
  }
}