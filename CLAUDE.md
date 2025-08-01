# CLAUDE.md - Video Rendering Intermediary Platform

## Project Overview
This project is an intermediary platform that sits between users and the Shotstack API for video rendering. Users make requests to our platform, which forwards them to Shotstack using our account, charging tokens from users.

## Architecture
- **Frontend**: Next.js 15 App Router with Shadcn UI (apps/web)
- **Backend**: Next.js API Routes + Supabase (apps/web)
- **Intermediary Service**: FastAPI Python service (apps/intermediary) 
- **Shared Types**: TypeScript shared package (packages/shared)
- **Database**: Supabase (PostgreSQL managed)
- **Authentication**: Supabase Auth (JWT-based)
- **Payments**: Stripe integration with token-based system
- **Cache/Queue**: Redis (for FastAPI workers)
- **UI Components**: Shadcn UI + Tailwind CSS

## Key Integrations
- **Supabase**: Database, Authentication, Real-time subscriptions
- **Shotstack API**: Video rendering service (x-api-key authentication)
- **Stripe**: Token-based billing system
- **n8n**: Users make API calls via n8n to render videos
- **Google Cloud Storage**: Automatic video storage and delivery

## User Flow
1. Users register/login via Supabase Auth (email/password, OAuth providers)
2. Users purchase tokens via Stripe integration
3. Frontend generates API keys for programmatic access
4. Users make API calls via n8n using their keys
5. Intermediary service validates key with Supabase, consumes tokens, and proxies to Shotstack
6. Videos are automatically transferred to Google Cloud Storage
7. Users get GCS URLs (Shotstack URLs are hidden from end users)

## Development Commands
- `npm run dev` - Start all development servers
- `npm run build` - Build all services
- `npm run lint` - Run linting
- `npm run type-check` - Run TypeScript compiler
- `npm run type:generate` - Generate Supabase types
- `npm run db:reset` - Reset Supabase database (development only)

## Environment Variables
### Web App (.env.local)
```
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Internal Services
INTERMEDIARY_SERVICE_URL=http://localhost:8001
INTERNAL_API_KEY=your-internal-api-key

# App Configuration
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
```

### Intermediary Service (.env)
```
# Supabase (for token validation)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Shotstack
SHOTSTACK_API_KEY=your-shotstack-key
SHOTSTACK_API_URL=https://api.shotstack.io/v1

# Redis & Services
REDIS_URL=redis://localhost:6379
WEB_SERVICE_URL=http://localhost:3000
INTERNAL_API_KEY=your-internal-api-key

# Google Cloud Storage
GCS_BUCKET=your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
```

## Core Features
1. **API Key Management**: Frontend for managing API keys
2. **Token System**: Stripe integration for token purchase and consumption
3. **Request Proxy**: FastAPI service that intermediates calls to Shotstack
4. **Rate Limiting**: Per-user rate limiting control
5. **Usage Analytics**: Usage tracking and billing
6. **Webhook Handling**: Shotstack and Stripe webhooks
7. **API Documentation**: Interactive Swagger UI documentation

## Tech Stack Details
- **Frontend**: Next.js 15, React, TypeScript, Tailwind CSS, Shadcn UI
- **Backend API**: Next.js API Routes + Supabase
- **Authentication**: Supabase Auth (email/password, OAuth providers)
- **Database**: Supabase (PostgreSQL managed)
- **Intermediary**: Python 3.11+, FastAPI, Redis, ARQ workers
- **Payments**: Stripe SDK with webhooks
- **Storage**: Google Cloud Storage (automatic video transfer)
- **UI Components**: Shadcn UI (radix-ui based components)
- **Validation**: Zod (TypeScript), Pydantic (Python)
- **API Documentation**: Swagger UI with OpenAPI 3.0
- **Testing**: Jest with TypeScript support
- **Real-time**: Supabase Realtime for live updates

## Security Considerations
- **Supabase Auth**: JWT validation with Row Level Security (RLS)
- **API Keys**: Hashed storage and secure generation
- **Service-to-Service Auth**: Internal API key between Next.js and FastAPI
- **Rate Limiting**: Per-user request limiting
- **Webhook Validation**: Stripe webhook signature verification
- **Environment Variables**: Secure secret management
- **CORS Configuration**: Restricted to known origins
- **Error Handling**: Structured error responses without sensitive data exposure
- **Input Validation**: Comprehensive validation with Zod schemas

## Database Schema (Supabase)
### Core Tables
- **users**: User profiles and authentication (managed by Supabase Auth)
- **api_keys**: User-generated API keys for programmatic access
- **credit_balance**: User token/credit balances
- **usage_logs**: API usage tracking and billing
- **renders**: Video render job history and metadata
- **stripe_customers**: Stripe customer ID mapping

### Row Level Security (RLS)
- Users can only access their own data
- API keys are validated against user ownership
- Usage logs are filtered by user context

## Service Integration Flow
```
User (Browser) → Next.js Frontend → Supabase Auth
     ↓                ↓                ↓
Next.js API Routes → Supabase DB → Row Level Security
     ↓
FastAPI Service → Shotstack API → Google Cloud Storage
     ↓                ↓              ↓
Redis Workers → Background Jobs → Video Transfer
```

## Project Structure (apps/web/src)
```
src/
├── app/                    # Next.js App Router
│   ├── api/               # API Routes endpoints
│   ├── docs/              # Swagger UI documentation
│   ├── layout.tsx         # Root layout
│   └── page.tsx           # Home page
├── functions/             # Business logic functions
│   └── error_handling/    # Error handling utilities
├── hooks/                 # Custom React hooks
│   ├── useAuth.ts         # Authentication hook
│   ├── useApiKeys.ts      # API keys management
│   ├── useTokens.ts       # Token management
│   └── useUsage.ts        # Usage analytics
├── routers/               # API route handlers
│   ├── auth.ts            # Authentication routes
│   └── apiKeys.ts         # API key routes
├── test/                  # Test files
│   └── api.test.ts        # API tests
├── types/                 # TypeScript type definitions
│   ├── supabase.ts        # Generated Supabase types
│   └── api.ts             # API-specific types
└── utils/                 # Utility functions
    ├── index.ts           # General utilities
    ├── supabase.ts        # Supabase client configuration
    ├── swagger.ts         # API documentation config
    └── validations.ts     # Zod schemas
```

## Component Architecture (Shadcn UI)
- **Dashboard**: Overview with charts and metrics
- **API Keys**: Key generation and management interface
- **Usage**: Historical usage and billing data
- **Profile**: User settings and account management
- **Billing**: Stripe integration for token purchases

## API Development Guidelines
### Adding New API Routes
1. Create route handler in `src/routers/`
2. Add Swagger documentation comments
3. Export named functions for HTTP methods
4. Use Zod for request validation
5. Update types in `src/types/api.ts`
6. Connect to Next.js API route in `src/app/api/`

### Error Handling Pattern
```typescript
import { handleApiError, errors } from '@/functions/error_handling'

export async function handleApiFunction(request: NextRequest) {
  try {
    // Your logic here
    if (!valid) {
      throw errors.badRequest('Invalid input')
    }
    return NextResponse.json({ success: true })
  } catch (error) {
    return handleApiError(error)
  }
}
```

### Using Custom Hooks
```typescript
import { useAuth } from '@/hooks/useAuth'
import { useApiKeys } from '@/hooks/useApiKeys'

// In components
const { user, signIn, signOut } = useAuth()
const { keys, createKey, deleteKey } = useApiKeys()
```

## Documentation Structure
- **CLAUDE.md**: Arquitetura técnica e guidelines de desenvolvimento
- **BUSINESS_RULES.md**: Regras de negócio detalhadas e validações
- **SUPABASE_SETUP.md**: Guia de configuração do Supabase
- **README.md**: Documentação geral do projeto

## Monitoring & Logging
- **Supabase**: Built-in database monitoring and analytics
- **Request/Response**: API route logging with user context
- **Token Consumption**: Real-time balance updates
- **Error Monitoring**: Structured error logging with user tracing
- **Performance Metrics**: API response times and throughput
- **API Documentation**: Interactive Swagger UI at `/docs`

## Key Documents
- Business Rules: `BUSINESS_RULES.md`