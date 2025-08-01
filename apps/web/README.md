# Shotstack Intermediary Web Application

Next.js 15 web application with Supabase authentication and Shadcn UI components for managing video rendering tokens and API keys.

## Features

- **🔐 Supabase Authentication**: Email/password and OAuth providers
- **🎨 Shadcn UI Components**: Modern, accessible React components
- **🔑 API Key Management**: Generate and manage API keys for programmatic access
- **💰 Token System**: Purchase and track token usage with Stripe integration
- **📊 Usage Analytics**: Track API usage and billing history
- **📚 API Documentation**: Interactive Swagger UI documentation

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + Shadcn UI
- **Authentication**: Supabase Auth
- **Database**: Supabase (PostgreSQL)
- **Payments**: Stripe
- **Validation**: Zod
- **API Docs**: Swagger UI

## Project Structure

```
src/
├── app/                    # Next.js App Router
│   ├── api/               # API Routes
│   │   ├── auth/          # Authentication endpoints
│   │   ├── api-keys/      # API key management
│   │   ├── tokens/        # Token purchases
│   │   ├── usage/         # Usage analytics
│   │   └── swagger/       # API documentation
│   ├── docs/              # Swagger UI page
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

## Getting Started

### Prerequisites

- Node.js 18+
- Supabase project
- Stripe account (for payments)

### Installation

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Environment Setup:**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your configuration
   ```

3. **Generate Supabase types:**
   ```bash
   npm run type:generate
   ```

4. **Start development server:**
   ```bash
   npm run dev
   ```

The application will be available at `http://localhost:3000`

## API Routes

### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/signin` - User login
- `POST /api/auth/signout` - User logout

### API Keys
- `GET /api/api-keys` - List user's API keys
- `POST /api/api-keys` - Create new API key
- `PUT /api/api-keys/:id` - Update API key
- `DELETE /api/api-keys/:id` - Delete API key

### Tokens
- `GET /api/tokens/balance` - Get current token balance
- `POST /api/tokens/purchase` - Purchase tokens via Stripe
- `POST /api/tokens/webhook` - Stripe webhook handler

### Usage
- `GET /api/usage/stats` - Get usage statistics
- `GET /api/usage/logs` - Get usage history

### Documentation
- `GET /api/swagger` - OpenAPI specification
- `GET /docs` - Interactive Swagger UI

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Yes |
| `STRIPE_SECRET_KEY` | Stripe secret key | Yes |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | Yes |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook secret | Yes |
| `INTERMEDIARY_SERVICE_URL` | FastAPI service URL | Yes |
| `INTERNAL_API_KEY` | Internal service authentication | Yes |
| `NEXTAUTH_SECRET` | NextAuth secret | Yes |
| `NEXTAUTH_URL` | Application URL | Yes |

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run type-check` - Run TypeScript compiler
- `npm run type:generate` - Generate Supabase types

## Directory Explanation

### `/functions`
Business logic and utility functions organized by functionality. Contains error handling, validation logic, and other reusable functions.

### `/hooks`
Custom React hooks for managing state and API interactions. Each hook handles a specific domain (auth, API keys, tokens, usage).

### `/routers`
API route handlers separated from Next.js API routes for better organization. Contains the actual business logic for each endpoint.

### `/test`
Test files for the application. Includes unit tests, integration tests, and API tests.

### `/utils`
General utility functions, configurations, and helpers used throughout the application.

## Database Schema

The application expects the following Supabase tables:

- **api_keys** - User-generated API keys
- **credit_balance** - User token balances
- **usage_logs** - API usage tracking
- **renders** - Video render history
- **stripe_customers** - Stripe customer mapping

See `src/types/supabase.ts` for complete schema definitions.

## Shadcn UI Components

This project uses Shadcn UI components for consistent, accessible design:

- Button, Card, Dialog, Dropdown
- Toast notifications
- Tabs, Avatar, Badge
- Form components with validation
- Charts for analytics (Recharts)

## Security

- **JWT Authentication**: Supabase Auth with Row Level Security
- **API Key Hashing**: Secure storage of API keys
- **CORS Configuration**: Restricted origins
- **Input Validation**: Zod schemas for all inputs
- **Environment Variables**: Secure secret management

## Development

### Adding New API Routes

1. Create route handler in `src/routers/`
2. Add Swagger documentation comments
3. Export named functions for HTTP methods
4. Use Zod for request validation
5. Update types in `src/types/api.ts`
6. Connect to Next.js API route in `src/app/api/`

### Adding New Hooks

1. Create hook file in `src/hooks/`
2. Follow existing patterns for state management
3. Use TypeScript for proper typing
4. Handle loading and error states

### Testing

Run tests with:
```bash
npm test
```

Tests are organized in the `/test` directory and follow Jest conventions.

## Production Deployment

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Set environment variables**
3. **Deploy to your platform** (Vercel, Netlify, etc.)
4. **Configure Supabase** with production URLs
5. **Set up Stripe webhooks** pointing to production

## API Documentation

Visit `/docs` when running the application to access interactive Swagger UI documentation.