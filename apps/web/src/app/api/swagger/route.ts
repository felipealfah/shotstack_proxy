import { NextResponse } from 'next/server'
import { swaggerSpec } from '@/utils/swagger'

/**
 * @swagger
 * /api/swagger:
 *   get:
 *     summary: Get OpenAPI specification
 *     description: Returns the OpenAPI 3.0 specification for the API
 *     tags:
 *       - Documentation
 *     responses:
 *       200:
 *         description: OpenAPI specification
 *         content:
 *           application/json:
 *             schema:
 *               type: object
 */
export async function GET() {
  return NextResponse.json(swaggerSpec)
}