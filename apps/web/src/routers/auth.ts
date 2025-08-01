import { NextRequest, NextResponse } from 'next/server'
import { createServerSupabaseClient } from '@/utils/supabase-server'
import { handleApiError, errors } from '@/functions/error_handling'

/**
 * @swagger
 * /api/auth/signup:
 *   post:
 *     summary: Register a new user
 *     tags:
 *       - Authentication
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *               - password
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *               password:
 *                 type: string
 *                 minLength: 6
 *     responses:
 *       201:
 *         description: User created successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 user:
 *                   $ref: '#/components/schemas/User'
 *                 message:
 *                   type: string
 *       400:
 *         description: Bad request
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleSignUp(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    if (!email || !password) {
      throw errors.badRequest('Email and password are required')
    }

    if (password.length < 6) {
      throw errors.badRequest('Password must be at least 6 characters')
    }

    const supabase = createServerSupabaseClient()
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${request.nextUrl.origin}/dashboard`
      }
    })

    if (error) {
      throw error
    }

    return NextResponse.json(
      {
        user: data.user,
        message: 'User created successfully. Please check your email for verification.'
      },
      { status: 201 }
    )
  } catch (error) {
    return handleApiError(error)
  }
}

/**
 * @swagger
 * /api/auth/signin:
 *   post:
 *     summary: Sign in user
 *     tags:
 *       - Authentication
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required:
 *               - email
 *               - password
 *             properties:
 *               email:
 *                 type: string
 *                 format: email
 *               password:
 *                 type: string
 *     responses:
 *       200:
 *         description: User signed in successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 user:
 *                   $ref: '#/components/schemas/User'
 *                 session:
 *                   type: object
 *       401:
 *         description: Invalid credentials
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
export async function handleSignIn(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    if (!email || !password) {
      throw errors.badRequest('Email and password are required')
    }

    const supabase = createServerSupabaseClient()
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })

    if (error) {
      throw errors.unauthorized()
    }

    return NextResponse.json({
      user: data.user,
      session: data.session
    })
  } catch (error) {
    return handleApiError(error)
  }
}

/**
 * @swagger
 * /api/auth/signout:
 *   post:
 *     summary: Sign out user
 *     tags:
 *       - Authentication
 *     security:
 *       - BearerAuth: []
 *     responses:
 *       200:
 *         description: User signed out successfully
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 *               properties:
 *                 message:
 *                   type: string
 */
export async function handleSignOut() {
  try {
    const supabase = createServerSupabaseClient()
    const { error } = await supabase.auth.signOut()

    if (error) {
      throw error
    }

    return NextResponse.json({
      message: 'User signed out successfully'
    })
  } catch (error) {
    return handleApiError(error)
  }
}