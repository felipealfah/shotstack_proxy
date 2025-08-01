import swaggerJSDoc from 'swagger-jsdoc'

const options: swaggerJSDoc.Options = {
  definition: {
    openapi: '3.0.0',
    info: {
      title: 'Shotstack Intermediary Platform API',
      version: '1.0.0',
      description: 'API documentation for the Shotstack Intermediary Platform - Token-based video rendering with Supabase authentication',
      contact: {
        name: 'API Support',
        email: 'support@example.com'
      }
    },
    servers: [
      {
        url: process.env.NODE_ENV === 'production' 
          ? 'https://your-domain.com' 
          : 'http://localhost:3000',
        description: process.env.NODE_ENV === 'production' 
          ? 'Production server' 
          : 'Development server'
      }
    ],
    components: {
      securitySchemes: {
        BearerAuth: {
          type: 'http',
          scheme: 'bearer',
          bearerFormat: 'JWT',
          description: 'Supabase JWT token'
        },
        ApiKeyAuth: {
          type: 'apiKey',
          in: 'header',
          name: 'X-API-Key',
          description: 'Generated API key for programmatic access'
        }
      },
      schemas: {
        User: {
          type: 'object',
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'User ID from Supabase Auth'
            },
            email: {
              type: 'string',
              format: 'email',
              description: 'User email address'
            },
            created_at: {
              type: 'string',
              format: 'date-time',
              description: 'Account creation timestamp'
            }
          }
        },
        ApiKey: {
          type: 'object',
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'API key ID'
            },
            name: {
              type: 'string',
              description: 'User-defined name for the API key'
            },
            key_hash: {
              type: 'string',
              description: 'Hashed API key (actual key not stored)'
            },
            created_at: {
              type: 'string',
              format: 'date-time',
              description: 'Key creation timestamp'
            },
            last_used: {
              type: 'string',
              format: 'date-time',
              nullable: true,
              description: 'Last usage timestamp'
            },
            is_active: {
              type: 'boolean',
              description: 'Whether the key is active'
            }
          }
        },
        CreditBalance: {
          type: 'object',
          properties: {
            user_id: {
              type: 'string',
              format: 'uuid',
              description: 'Associated user ID'
            },
            balance: {
              type: 'integer',
              description: 'Current token balance'
            },
            updated_at: {
              type: 'string',
              format: 'date-time',
              description: 'Last balance update'
            }
          }
        },
        UsageLog: {
          type: 'object',
          properties: {
            id: {
              type: 'string',
              format: 'uuid',
              description: 'Usage log ID'
            },
            user_id: {
              type: 'string',
              format: 'uuid',
              description: 'User who made the request'
            },
            api_key_id: {
              type: 'string',
              format: 'uuid',
              description: 'API key used for the request'
            },
            endpoint: {
              type: 'string',
              description: 'API endpoint called'
            },
            tokens_consumed: {
              type: 'integer',
              description: 'Number of tokens used'
            },
            created_at: {
              type: 'string',
              format: 'date-time',
              description: 'Request timestamp'
            }
          }
        },
        Error: {
          type: 'object',
          properties: {
            error: {
              type: 'string',
              description: 'Error message'
            },
            code: {
              type: 'string',
              description: 'Error code'
            }
          }
        }
      }
    },
    security: [
      {
        BearerAuth: []
      }
    ]
  },
  apis: [
    './src/app/api/**/*.ts',
    './src/routers/**/*.ts'
  ]
}

export const swaggerSpec = swaggerJSDoc(options)