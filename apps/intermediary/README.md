# Shotstack Intermediary Service

A FastAPI service that acts as an intermediary between users and the Shotstack API for video rendering, with automatic Google Cloud Storage integration and token-based billing.

## Features

- **Video Rendering**: Proxy requests to Shotstack API with authentication
- **Automatic GCS Transfer**: Videos are automatically transferred to Google Cloud Storage
- **Token-based Billing**: Users are charged tokens for each render
- **JWT Authentication**: Secure API access with JWT tokens
- **Rate Limiting**: Per-user rate limiting control
- **Background Processing**: Asynchronous video transfer using ARQ workers
- **Usage Analytics**: Track usage and billing

## API Endpoints

### Health Check
- `GET /health` - Service health status

### Shotstack Proxy
- `POST /api/v1/render` - Create render job (requires API key, auto-configures GCS storage)
- `GET /api/v1/job/{job_id}` - Get job status from Redis queue (requires API key)
- `GET /api/v1/videos/{job_id}` - Get video download links (prioritizes GCS URLs)
- `GET /api/v1/render/{render_id}` - Get render status directly from Shotstack (requires API key)
- `POST /api/v1/webhook` - Handle Shotstack webhooks

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

3. **Setup Google Cloud Storage:**
   - Create a service account with Storage Admin permissions
   - Download the JSON credentials file
   - Copy `gcp-credentials.example.json` to `gcp-credentials.json`
   - Replace the example values with your actual credentials
   - Or set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

4. **Run Development Server**
   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SHOTSTACK_API_KEY` | Your Shotstack API key | Required |
| `SHOTSTACK_API_URL` | Shotstack API base URL | `https://api.shotstack.io/v1` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `WEB_SERVICE_URL` | Web service URL for API validation | `http://localhost:3000` |
| `JWT_SECRET` | JWT secret for authentication | Required |
| `API_HOST` | Host to bind the server | `0.0.0.0` |
| `API_PORT` | Port to bind the server | `8000` |
| `ENVIRONMENT` | Environment (development/production) | `development` |
| `RATE_LIMIT_REQUESTS` | Requests per window | `100` |
| `RATE_LIMIT_WINDOW` | Rate limit window in seconds | `3600` |
| `GCS_BUCKET` | Google Cloud Storage bucket name | `ffmpeg-api` |
| `GCS_PATH_PREFIX` | Path prefix for organized storage | `videos` |
| `GCS_ACL` | Access control for GCS files | `publicRead` |

## Docker

Build and run with Docker:

```bash
docker build -t shotstack-intermediary .
docker run -p 8000:8000 --env-file .env shotstack-intermediary
```

## Google Cloud Storage Integration

The service automatically configures Google Cloud Storage as the primary destination for all rendered videos:

### Features
- **Automatic Configuration**: All renders are automatically sent to GCS without user intervention
- **Organized Storage**: Files are stored with organized paths: `videos/{year}/{month}/{user_id}/video_{job_id}.mp4`
- **Public Access**: Videos are stored with public read access for easy sharing
- **Dual Storage**: Videos are stored in both GCS and Shotstack CDN for redundancy
- **Priority URLs**: The `/videos/{job_id}` endpoint prioritizes GCS URLs over Shotstack CDN

### Setup Requirements
1. Create a Google Cloud Storage bucket
2. Configure Shotstack to use your GCS credentials (done in Shotstack dashboard)
3. Set the bucket name in `GCS_BUCKET` environment variable
4. Configure desired access permissions in `GCS_ACL`

### URL Structure
GCS URLs follow the pattern:
```
https://storage.googleapis.com/{bucket_name}/videos/{year}/{month}/user_{user_id}/video_{job_id}.mp4
```

## Architecture

The service integrates with:

1. **Web Service** - For API key validation and token management
2. **Shotstack API** - For video rendering operations
3. **Google Cloud Storage** - For permanent video storage
4. **Redis** - For rate limiting and caching
5. **PostgreSQL** - For persistent data (via web service)

## Authentication Flow

1. User includes API key in `Authorization: Bearer <api_key>` header
2. Service validates API key with web service
3. Service checks user's token balance
4. If valid and sufficient tokens, request is proxied to Shotstack
5. Tokens are consumed and usage is logged

## Rate Limiting

- Uses Redis sliding window algorithm
- Configurable requests per time window
- Per-API key rate limiting
- Graceful degradation if Redis is unavailable