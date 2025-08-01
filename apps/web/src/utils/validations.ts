import { z } from 'zod'

export const createApiKeySchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .max(50, 'Name must be less than 50 characters')
    .regex(/^[a-zA-Z0-9\s\-_]+$/, 'Name can only contain letters, numbers, spaces, hyphens, and underscores')
})

export const tokenPurchaseSchema = z.object({
  amount: z.number()
    .min(100, 'Minimum purchase is $1.00') // $1 in cents
    .max(100000, 'Maximum purchase is $1,000.00'), // $1000 in cents
  token_count: z.number()
    .min(1, 'Must purchase at least 1 token')
    .max(100000, 'Cannot purchase more than 100,000 tokens at once')
})

export const usageStatsQuerySchema = z.object({
  start_date: z.string().datetime().optional(),
  end_date: z.string().datetime().optional(),
  limit: z.number().min(1).max(1000).default(100).optional()
})

export const updateApiKeySchema = z.object({
  name: z.string()
    .min(1, 'Name is required')
    .max(50, 'Name must be less than 50 characters')
    .regex(/^[a-zA-Z0-9\s\-_]+$/, 'Name can only contain letters, numbers, spaces, hyphens, and underscores')
    .optional(),
  is_active: z.boolean().optional()
})

export type CreateApiKeyInput = z.infer<typeof createApiKeySchema>
export type TokenPurchaseInput = z.infer<typeof tokenPurchaseSchema>
export type UsageStatsQuery = z.infer<typeof usageStatsQuerySchema>
export type UpdateApiKeyInput = z.infer<typeof updateApiKeySchema>