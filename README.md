# Shotstack Intermediary Platform

An intelligent intermediary platform that sits between users and the Shotstack API for video rendering, providing token-based billing, automatic transcription capabilities, and seamless Google Cloud Storage integration.

## 🏗️ Architecture

```
Users (n8n) → Next.js Frontend → FastAPI Intermediary → Shotstack API
                     ↓                    ↓
               Supabase DB         Background Worker → Google Cloud Storage
                     ↓                    ↓
               Stripe Billing         Redis Queue
```

## 📦 Services

### 🌐 `/apps/web` - React + Vite Frontend
- **Framework**: React 18 + Vite with TypeScript
- **Features**: User dashboard, token purchase, API key management, real-time metrics
- **Database**: Supabase (PostgreSQL managed)
- **Payments**: Stripe integration
- **Authentication**: Supabase Auth with dual authentication
- **UI**: Shadcn UI components + Tailwind CSS
- **Dashboard**: Real-time video management with expiration tracking

### ⚡ `/apps/intermediary` - FastAPI Service
- **Framework**: FastAPI (Python)
- **Features**: Intelligent request proxying, comprehensive payload validation, automatic transcription support
- **Queue**: Redis with ARQ workers for background processing
- **Storage**: Automatic Google Cloud Storage integration with 2-day lifecycle
- **Authentication**: Dual Email + API Key validation with Supabase
- **Validation**: Pydantic models supporting all Shotstack features including smart clips

## 🚀 Quick Start with Docker

### Prerequisites
- Docker & Docker Compose
- **Supabase project** (required for database and auth)
- Stripe account
- Google Cloud Storage bucket
- Shotstack API key

### Development Setup

1. **Setup Supabase project:**
   ```bash
   # Create project at https://supabase.com
   # Run the SQL schema in Supabase SQL Editor
   cat scripts/supabase-schema.sql
   ```

2. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd ss_inter
   cp .env.example .env
   # Edit .env with your Supabase configuration
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Web App: http://localhost:3000
   - API Documentation: http://localhost:3000/docs
   - Intermediary API: http://localhost:8001
   - Redis Commander: http://localhost:8081 (development only)

5. **View logs:**
   ```bash
   docker-compose logs -f [service-name]
   ```

### Production Deployment

1. **Production environment:**
   ```bash
   cp .env.example .env.production
   # Edit with production values
   docker-compose -f docker-compose.yml up -d
   ```

## 🐳 Docker Services

| Service | Port | Description |
|---------|------|-------------|
| `web` | 3000 | Next.js web application |
| `api` | 8001 | FastAPI intermediary service |
| `worker` | - | ARQ background worker |
| `redis` | 6379 | Redis cache and queue |
| `redis-commander` | 8081 | Redis UI (dev only) |

**Note**: Database is managed by Supabase (cloud-hosted PostgreSQL)

## 🔧 Key Features

- **🎬 Video Rendering**: Proxy requests to Shotstack with intelligent payload validation
- **🎤 Automatic Transcription**: Caption generation from audio using Shotstack's AI transcription
- **☁️ Auto GCS Transfer**: Videos automatically transferred to Google Cloud Storage  
- **💰 Token Billing**: Users charged tokens per render with proportional pricing
- **🔐 Dual Authentication**: Email + API Key security system with Row Level Security
- **⚡ Background Jobs**: Async video transfer using ARQ workers
- **📊 Real-time Dashboard**: Live metrics and video management interface
- **🚦 Rate Limiting**: Per-user request limiting
- **🔍 Smart Validation**: Comprehensive payload validation supporting all Shotstack features
- **📚 API Documentation**: Interactive Swagger UI

## 📋 Docker Commands

### Development
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d web

# View logs
docker-compose logs -f api

# Restart service
docker-compose restart worker

# Stop all services
docker-compose down

# Rebuild and start
docker-compose up -d --build
```

### Database Management
```bash
# Database is managed by Supabase
# Access via Supabase dashboard: https://supabase.com/dashboard

# Reset database schema (run in Supabase SQL Editor)
cat scripts/supabase-schema.sql
```

### Production
```bash
# Production build and deploy
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml up -d

# Scale workers
docker-compose up -d --scale worker=3
```

## 🔗 API Usage

**Render a video with automatic transcription:**
```bash
curl -X POST "http://localhost:8002/api/v1/render" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "X-User-Email: user@example.com" \
  -H "Content-Type: application/json" \
  -d '{
    "timeline": {
      "tracks": [{
        "clips": [{
          "asset": {"type": "caption", "src": "alias://audioTrack"},
          "start": 0, "length": "end"
        }]
      }, {
        "clips": [{
          "asset": {"type": "audio", "src": "https://example.com/audio.mp3"},
          "start": 0, "length": "auto", "alias": "audioTrack"
        }]
      }]
    },
    "output": {"format": "mp4", "size": {"width": 1280, "height": 720}}
  }'
```

**Get video links:**
```bash
curl "http://localhost:8002/api/v1/videos/{job_id}" \
  -H "Authorization: Bearer <your-api-key>" \
  -H "X-User-Email: user@example.com"
```

## 🏗️ Project Structure

```
.
├── apps/
│   ├── web/                    # Next.js application
│   │   ├── src/
│   │   │   ├── app/           # App Router pages and API routes
│   │   │   ├── functions/     # Business logic functions
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   ├── routers/       # API route handlers
│   │   │   ├── test/          # Test files
│   │   │   ├── types/         # TypeScript definitions
│   │   │   └── utils/         # Utility functions
│   │   ├── Dockerfile
│   │   └── package.json
│   └── intermediary/           # FastAPI service
│       ├── app/
│       ├── Dockerfile
│       └── requirements.txt
├── scripts/                    # Database and deployment scripts
├── docker-compose.yml          # Main Docker Compose configuration
├── docker-compose.override.yml # Development overrides
├── .env.example               # Environment variables template
└── README.md
```

## 🔐 Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Supabase (get from your project dashboard)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DATABASE_URL=postgresql://postgres.your-project-id:password@aws-0-region.pooler.supabase.com:6543/postgres

# Shotstack
SHOTSTACK_API_KEY=your-shotstack-api-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google Cloud Storage
GCS_BUCKET=your-bucket-name
GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials.json
```

## 🔒 Security & Production

- Dual authentication with Email + API Key validation
- JWT token validation with Supabase Row Level Security
- Comprehensive payload validation with Pydantic models
- Per-user rate limiting and resource isolation
- Environment variable protection
- CORS configuration
- Webhook signature validation
- Structured logging and monitoring
- Health checks for all services

## 📚 Documentation

- [Web Application README](apps/web/README.md)
- [Intermediary Service README](apps/intermediary/README.md)
- [API Documentation](http://localhost:3000/docs) (when running)

## 🤝 Development

### Adding New Services
1. Create service directory in `apps/`
2. Add Dockerfile
3. Update `docker-compose.yml`
4. Add environment variables to `.env.example`

### Debugging
```bash
# View service logs
docker-compose logs -f service-name

# Execute commands in container
docker-compose exec web bash
docker-compose exec api python -c "import app; print('API loaded')"

# Check service health
curl http://localhost:3000/api/health
curl http://localhost:8001/health
```

## 🚨 Troubleshooting

**Port conflicts:**
```bash
# Check what's using ports
sudo lsof -i :3000
sudo lsof -i :8001

# Use different ports
WEB_PORT=3001 API_PORT=8002 docker-compose up -d
```

**Database connection issues:**
```bash
# Check Supabase connection settings in .env
# Verify your Supabase project is active
# Check connection string format in .env.example
```

**Build failures:**
```bash
# Clean rebuild
docker-compose down
docker system prune -f
docker-compose build --no-cache
docker-compose up -d
```

For more detailed setup instructions, see individual service READMEs.