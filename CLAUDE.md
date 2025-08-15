# CLAUDE.md - Video Rendering Intermediary Platform

## Project Overview
This project is an intermediary platform that sits between users and the Shotstack API for video rendering. Users make requests to our platform, which forwards them to Shotstack using our account, charging tokens from users.

## Architecture
- **Frontend**: React 18 + Vite + TypeScript with Shadcn UI (apps/web)
- **Backend**: FastAPI Python service (apps/intermediary) + Supabase
- **Database**: Supabase (PostgreSQL managed) - `hjwchewuibqpoeggynwp.supabase.co`
- **Authentication**: Supabase Auth (JWT-based)
- **Payments**: Stripe integration with token-based system
- **Cache/Queue**: Redis + ARQ (for background workers)
- **Storage**: Google Cloud Storage (`ffmpeg-api` bucket)
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
6. ARQ workers process render jobs in background
7. Videos are automatically transferred to Google Cloud Storage (`ffmpeg-api` bucket)
8. Users get GCS URLs (Shotstack URLs are hidden from end users)

**✅ N8N Integration Status: COMPLETE AND VALIDATED**

## Development Commands
- `docker-compose up --build` - Start all development servers (preferred)
- `npm run dev` - Start frontend only (React + Vite)
- `npm run build` - Build all services
- `npm run lint` - Run linting
- `npm run type-check` - Run TypeScript compiler
- `npm run type:generate` - Generate Supabase types
- `npm run db:reset` - Reset Supabase database (development only)

## Docker Services
- **API**: Port 8002 (FastAPI intermediary service)
- **Web**: Port 3003 (React + Vite frontend)
- **Worker**: ARQ background worker for video processing
- **Redis**: Job queue and caching

## Environment Variables
### Web App (.env)
```
# Supabase (unified configuration)
VITE_SUPABASE_URL=https://hjwchewuibqpoeggynwp.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key

# API Service
VITE_API_URL=http://localhost:8002
```

### Intermediary Service (.env)
```
# Supabase (unified configuration)
SUPABASE_URL=https://hjwchewuibqpoeggynwp.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Shotstack
SHOTSTACK_API_KEY=your-shotstack-key
SHOTSTACK_API_URL=https://api.shotstack.io/v1

# Redis & Workers
REDIS_URL=redis://redis:6379

# Google Cloud Storage (validated)
GCS_BUCKET=ffmpeg-api
GCS_PATH_PREFIX=videos
GCS_ACL=publicRead
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development
```

## Core Features

### ✅ Implemented and Working
1. **API Key Management**: Frontend for managing API keys ✅
2. **Token System**: Token consumption and validation ✅
3. **Request Proxy**: FastAPI service that intermediates calls to Shotstack ✅
4. **Rate Limiting**: Per-user rate limiting control ✅
5. **Background Processing**: ARQ workers for video rendering ✅
6. **GCS Transfer**: Automatic video transfer to Google Cloud Storage ✅
7. **N8N Integration**: Complete workflow integration ✅
8. **API Documentation**: Interactive Swagger UI documentation ✅

### 🚧 Next Development Phase
1. **Dashboard Cards Integration**: Connect cards with real database metrics
2. **Recent Videos Area**: List of recently rendered videos with download links
3. **Video Lifecycle Management**: 24-hour expiration system for videos
4. **Usage Analytics**: Detailed usage tracking and billing dashboard
5. **Stripe Integration**: Token purchase frontend
6. **Webhook Handling**: Shotstack and Stripe webhooks

## Tech Stack Details
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI + Python 3.11+ + Supabase
- **Authentication**: Supabase Auth (email/password, OAuth providers)
- **Database**: Supabase (PostgreSQL managed) - `hjwchewuibqpoeggynwp.supabase.co`
- **Background Jobs**: Redis + ARQ workers for video processing
- **Video Processing**: Shotstack API integration
- **Storage**: Google Cloud Storage (`ffmpeg-api` bucket)
- **UI Components**: Shadcn UI (radix-ui based components)
- **Validation**: Pydantic (Python)
- **API Documentation**: Swagger UI with OpenAPI 3.0
- **Containerization**: Docker + Docker Compose
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
User (Browser) → React Frontend → Supabase Auth
     ↓                ↓              ↓
     ↓         API Key Generation → Supabase DB (RLS)
     ↓
N8N Workflow → FastAPI Service → Token Validation (Supabase)
     ↓                ↓                    ↓
   ARQ Job → Redis Queue → Background Worker
     ↓                ↓            ↓
Shotstack API → Video Render → GCS Transfer
     ↓                ↓            ↓
Public Video URL ← ffmpeg-api bucket ← Automatic Transfer
```

## Project Structure (apps/web/src)
```
src/
├── components/            # React components
│   ├── ui/               # Shadcn UI components
│   ├── layout/           # Layout components (Header, Sidebar)
│   └── features/         # Feature-specific components
├── pages/                 # Route components (React Router)
│   ├── HomePage.tsx       # Landing page
│   ├── LoginPage.tsx      # Authentication
│   ├── DashboardPage.tsx  # Main dashboard
│   └── ApiKeysPage.tsx    # API key management
├── hooks/                 # Custom React hooks
│   ├── useAuth.ts         # Authentication hook (Supabase)
│   ├── useApi.ts          # HTTP client hook
│   ├── useApiKeys.ts      # API keys management
│   ├── useTokens.ts       # Token management
│   └── useUsage.ts        # Usage analytics
├── services/              # API integration
│   ├── api.ts             # FastAPI client
│   ├── auth.ts            # Supabase auth service
│   └── stripe.ts          # Payment integration
├── utils/                 # Utility functions
│   ├── supabase.ts        # Supabase client configuration
│   ├── constants.ts       # App constants
│   └── validations.ts     # Zod schemas
├── types/                 # TypeScript type definitions
│   ├── supabase.ts        # Generated Supabase types
│   └── api.ts             # API-specific types
├── App.tsx                # Main app component
├── main.tsx               # Vite entry point
└── router.tsx             # React Router configuration
```

## Component Architecture (Shadcn UI)
- **Dashboard**: Overview with charts and metrics
- **API Keys**: Key generation and management interface
- **Usage**: Historical usage and billing data
- **Profile**: User settings and account management
- **Billing**: Stripe integration for token purchases

## Frontend Development Guidelines

### Adding New Pages/Routes
1. Create page component in `src/pages/`
2. Add route to `src/router.tsx`
3. Use React Router hooks for navigation
4. Implement proper loading and error states
5. Update types in `src/types/api.ts`

### API Integration Pattern
```typescript
import { useApi } from '@/hooks/useApi'

export function useApiKeys() {
  const { get, post, del } = useApi()
  
  const getKeys = async () => {
    return await get('/api/api-keys')
  }
  
  const createKey = async (data: CreateKeyData) => {
    return await post('/api/api-keys', data)
  }
  
  return { getKeys, createKey }
}
```

### Using Custom Hooks
```typescript
import { useAuth } from '@/hooks/useAuth'
import { useApiKeys } from '@/hooks/useApiKeys'

// In components
const { user, signIn, signOut } = useAuth()
const { keys, createKey, deleteKey, loading } = useApiKeys()
```

### Backend API Development (FastAPI)
1. Add endpoints in FastAPI service
2. Include Swagger documentation
3. Use Pydantic models for validation
4. Implement proper error handling
5. Add CORS configuration for frontend

## Documentation Structure
- **CLAUDE.md**: Arquitetura técnica e guidelines de desenvolvimento
- **BUSINESS_RULES.md**: Regras de negócio detalhadas e validações
- **plan/plan.md**: Status geral e funcionalidades (roadmap)
- **plan/TODO.md**: Implementação técnica detalhada (guia de desenvolvimento)
- **README.md**: Documentação geral do projeto

## Monitoring & Logging
- **Supabase**: Built-in database monitoring and analytics
- **Request/Response**: API route logging with user context
- **Token Consumption**: Real-time balance updates
- **Error Monitoring**: Structured error logging with user tracing
- **Performance Metrics**: API response times and throughput
- **API Documentation**: Interactive Swagger UI at `/docs`

## Key Documents
- **Business Rules**: `BUSINESS_RULES.md` - Regras de negócio e validações
- **Development Plan**: `plan/plan.md` - Status geral e funcionalidades (roadmap)
- **Technical TODO**: `plan/TODO.md` - Implementação técnica detalhada com código

## Next Development Phase
Para implementar as próximas funcionalidades do dashboard, consulte o planejamento técnico detalhado:

### 📊 Dashboard Cards Integration
- **Guia Técnico**: [`plan/TODO.md#dashboard-cards-integration`](plan/TODO.md#-dashboard-cards-integration)
- **Hooks React**: `useActiveRenders()`, `useCompletedVideos()`, `useTokenBalance()`
- **Queries Supabase**: Otimizadas com exemplos SQL

### 🎬 Recent Videos Area  
- **Guia Técnico**: [`plan/TODO.md#recent-videos-area`](plan/TODO.md#-recent-videos-area)
- **Componente**: `RecentVideos.tsx` com badges de expiração
- **API**: Endpoint com cálculo dinâmico de expiração

### ⏰ Video Lifecycle (24h)
- **Guia Técnico**: [`plan/TODO.md#video-lifecycle-management-24h`](plan/TODO.md#-video-lifecycle-management-24h)  
- **Database**: Schema updates e cron jobs
- **GCS**: Lifecycle policy para auto-delete