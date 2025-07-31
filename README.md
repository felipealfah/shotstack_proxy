# Shotstack Intermediary Platform

An intermediary platform that sits between users and the Shotstack API for video rendering, providing token-based billing and automatic Google Cloud Storage integration.

## 🏗️ Architecture

```
Users (n8n) → Next.js Frontend → FastAPI Intermediary → Shotstack API
                     ↓                    ↓
               PostgreSQL DB    Background Worker → Google Cloud Storage
                     ↓                    ↓
               Stripe Billing         Redis Queue
```

## 📦 Services

### 🌐 `/apps/web` - Next.js Frontend + Backend
- **Framework**: Next.js 15 App Router
- **Features**: User registration, token purchase, API key management
- **Database**: PostgreSQL with Prisma ORM
- **Payments**: Stripe integration
- **Authentication**: NextAuth.js

### ⚡ `/apps/intermediary` - FastAPI Service
- **Framework**: FastAPI (Python)
- **Features**: Request proxying, token validation, video transfer
- **Queue**: Redis with ARQ workers
- **Storage**: Automatic Google Cloud Storage integration
- **Authentication**: JWT validation

### 📊 `/packages/shared` - Shared Types
- **Framework**: TypeScript
- **Features**: Shared types and utilities between services

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- PostgreSQL
- Redis
- Docker & Docker Compose

### Development Setup

1. **Clone and install:**
   ```bash
   git clone <repository-url>
   cd ss_inter
   npm install
   ```

2. **Environment setup:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Database setup:**
   ```bash
   npm run db:generate
   npm run db:push
   ```

4. **Start all services:**
   ```bash
   npm run dev
   ```

### Production Deployment

```bash
docker-compose up -d
```

## 🔧 Key Features

- **🎬 Video Rendering**: Proxy requests to Shotstack with authentication
- **☁️ Auto GCS Transfer**: Videos automatically transferred to Google Cloud Storage  
- **💰 Token Billing**: Users charged tokens per render
- **🔐 JWT Auth**: Secure API access with JWT tokens
- **⚡ Background Jobs**: Async video transfer using ARQ workers
- **📊 Analytics**: Usage tracking and billing
- **🚦 Rate Limiting**: Per-user request limiting

## 📋 Available Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start all development servers |
| `npm run build` | Build all services |
| `npm run lint` | Run linting across all services |
| `npm run db:generate` | Generate Prisma client |
| `npm run db:push` | Push schema to database |
| `npm run db:migrate` | Run database migrations |

## 🔗 API Usage

**Render a video:**
```bash
curl -X POST "http://localhost:8001/api/v1/render" \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "timeline": {
      "tracks": [{
        "clips": [{
          "asset": {"type": "video", "src": "https://example.com/video.mp4"},
          "start": 0, "length": 10
        }]
      }]
    },
    "output": {"format": "mp4", "size": {"width": 1280, "height": 720}}
  }'
```

**Get video links:**
```bash
curl "http://localhost:8001/api/v1/videos/{job_id}" \
  -H "Authorization: Bearer <jwt-token>"
```

## 📚 Documentation

- [Intermediary Service Documentation](apps/intermediary/README.md)
- [Web Application Documentation](apps/web/README.md)

## 🔐 Security & Production

- JWT token validation
- Per-user rate limiting  
- Environment variable protection
- CORS configuration
- Webhook signature validation
- Structured logging and monitoring

## 🤝 Getting Started

Check individual service READMEs for detailed setup instructions:
- [Intermediary Setup](apps/intermediary/README.md)
- [Web App Setup](apps/web/README.md)