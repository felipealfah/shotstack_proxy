# CLAUDE.md - Video Rendering Intermediary Platform

## Project Overview
This project is an intermediary platform that sits between users and the Shotstack API for video rendering. Users make requests to our platform, which forwards them to Shotstack using our account, charging tokens from users.

## Architecture
- **Frontend + Backend**: Next.js 15 App Router (apps/web)
- **Intermediary Service**: FastAPI Python service (apps/intermediary) 
- **Shared Types**: TypeScript shared package (packages/shared)
- **Database**: PostgreSQL + Prisma ORM
- **Payments**: Stripe integration with token-based system
- **Cache/Queue**: Redis

## Key Integrations
- **Shotstack API**: Video rendering service (x-api-key authentication)
- **Stripe**: Token-based billing system
- **n8n**: Users make API calls via n8n to render videos

## User Flow
1. Users register on the frontend and purchase tokens via Stripe
2. Frontend generates API keys for account validation
3. Users make API calls via n8n using their keys
4. Intermediary service validates key, consumes tokens, and proxies to Shotstack
5. Shotstack webhooks return rendering status

## Development Commands
- `npm run dev` - Start all development servers
- `npm run build` - Build all services
- `npm run lint` - Run linting
- `npm run db:generate` - Generate Prisma client
- `npm run db:push` - Push schema to database
- `npm run db:migrate` - Run database migrations

## Environment Variables
### Web App (.env.local)
```
DATABASE_URL=postgresql://user:password@localhost:5432/ss_inter
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=http://localhost:3000
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
INTERMEDIARY_SERVICE_URL=http://localhost:8000
```

### Intermediary Service (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/ss_inter
SHOTSTACK_API_KEY=your-shotstack-key
SHOTSTACK_API_URL=https://api.shotstack.io/v1
REDIS_URL=redis://localhost:6379
WEB_SERVICE_URL=http://localhost:3000
JWT_SECRET=your-jwt-secret
```

## Core Features
1. **API Key Management**: Frontend for managing API keys
2. **Token System**: Stripe integration for token purchase and consumption
3. **Request Proxy**: FastAPI service that intermediates calls to Shotstack
4. **Rate Limiting**: Per-user rate limiting control
5. **Usage Analytics**: Usage tracking and billing
6. **Webhook Handling**: Shotstack and Stripe webhooks

## Tech Stack Details
- **Frontend**: Next.js 15, React, TypeScript, Tailwind CSS
- **Backend API**: Next.js API Routes
- **Intermediary**: Python 3.11+, FastAPI, SQLAlchemy, Redis
- **Database**: PostgreSQL, Prisma ORM
- **Authentication**: NextAuth.js + JWT for API validation
- **Payments**: Stripe SDK
- **Validation**: Zod (TypeScript), Pydantic (Python)

## Security Considerations
- API keys with JWT validation
- Per-user rate limiting
- Webhook signature validation
- Environment variable protection
- CORS configuration

## Monitoring & Logging
- Request/response logging
- Token consumption tracking
- Error monitoring
- Performance metrics