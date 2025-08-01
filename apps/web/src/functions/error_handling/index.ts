import { NextResponse } from 'next/server'
import { ZodError } from 'zod'

export interface ApiError {
  error: string
  code?: string
  details?: any
}

export class AppError extends Error {
  public statusCode: number
  public code?: string
  public isOperational: boolean

  constructor(message: string, statusCode: number = 500, code?: string) {
    super(message)
    this.statusCode = statusCode
    this.code = code
    this.isOperational = true

    Error.captureStackTrace(this, this.constructor)
  }
}

export function handleApiError(error: unknown): NextResponse<ApiError> {
  console.error('API Error:', error)

  // Zod validation errors
  if (error instanceof ZodError) {
    return NextResponse.json(
      {
        error: 'Validation failed',
        code: 'VALIDATION_ERROR',
        details: error.errors
      },
      { status: 400 }
    )
  }

  // Custom application errors
  if (error instanceof AppError) {
    return NextResponse.json(
      {
        error: error.message,
        code: error.code
      },
      { status: error.statusCode }
    )
  }

  // Supabase errors
  if (error && typeof error === 'object' && 'message' in error) {
    const supabaseError = error as { message: string; code?: string }
    return NextResponse.json(
      {
        error: supabaseError.message,
        code: supabaseError.code || 'SUPABASE_ERROR'
      },
      { status: 400 }
    )
  }

  // Generic errors
  return NextResponse.json(
    {
      error: 'Internal server error',
      code: 'INTERNAL_ERROR'
    },
    { status: 500 }
  )
}

export function createApiError(message: string, statusCode: number = 500, code?: string) {
  return new AppError(message, statusCode, code)
}

// Common error responses
export const errors = {
  unauthorized: () => createApiError('Unauthorized', 401, 'UNAUTHORIZED'),
  forbidden: () => createApiError('Forbidden', 403, 'FORBIDDEN'),
  notFound: (resource?: string) => createApiError(
    resource ? `${resource} not found` : 'Resource not found', 
    404, 
    'NOT_FOUND'
  ),
  badRequest: (message: string) => createApiError(message, 400, 'BAD_REQUEST'),
  conflict: (message: string) => createApiError(message, 409, 'CONFLICT'),
  insufficientTokens: () => createApiError(
    'Insufficient token balance', 
    402, 
    'INSUFFICIENT_TOKENS'
  ),
  rateLimitExceeded: () => createApiError(
    'Rate limit exceeded', 
    429, 
    'RATE_LIMIT_EXCEEDED'
  )
}