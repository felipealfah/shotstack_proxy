from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv
from arq import create_pool
from arq.connections import RedisSettings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from .config import settings
from .routers import shotstack, health, expiration, gcp_sync
from .middleware.auth import verify_api_key
from .middleware.rate_limit import RateLimitMiddleware
from .services.expiration_service import run_expiration_sync, run_cleanup
from .services.gcp_sync_service import run_gcp_sync_fallback

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create Redis connection pool
    app.state.redis_pool = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_URL)
    )
    
    # Startup: Initialize and start scheduler for video expiration
    scheduler = AsyncIOScheduler()
    
    # Run expiration sync (configurável via ENV)
    scheduler.add_job(
        run_expiration_sync,
        'cron',
        hour=settings.EXPIRATION_SYNC_CRON_HOURS,  # Configurável via .env
        minute=0,
        id='expiration_sync',
        replace_existing=True
    )
    
    # Run cleanup of old records once daily (configurável via ENV)
    scheduler.add_job(
        run_cleanup,
        'cron',
        hour=settings.CLEANUP_JOB_CRON_HOUR,  # Configurável via .env
        minute=0,
        id='cleanup_old_records',
        replace_existing=True
    )
    
    # Run GCP sync fallback every hour (configurável via ENV)
    if settings.GCP_SYNC_ENABLED:
        scheduler.add_job(
            run_gcp_sync_fallback,
            'cron',
            minute=0,  # Todo início de hora (0 min)
            id='gcp_sync_fallback',
            replace_existing=True
        )
        logger.info("GCP sync fallback cron job enabled")
    else:
        logger.info("GCP sync fallback is disabled via GCP_SYNC_ENABLED=false")
    
    scheduler.start()
    app.state.scheduler = scheduler
    logger.info(f"Schedulers started - Expiration sync: {settings.EXPIRATION_SYNC_CRON_HOURS}h, Cleanup: {settings.CLEANUP_JOB_CRON_HOUR}h, GCP Sync: hourly")
    
    yield
    
    # Shutdown: Stop scheduler and close Redis connection
    scheduler.shutdown()
    await app.state.redis_pool.close()
    logger.info("Application shutdown complete")

app = FastAPI(
    title="Shotstack Intermediary API",
    description="Intermediary service for Shotstack video rendering with token-based billing. Supports high concurrency and multiple simultaneous requests.",
    version="1.0.0",
    lifespan=lifespan,
    # Configuração para múltiplas requisições simultâneas
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])

# Main shotstack router with authentication
app.include_router(
    shotstack.router, 
    prefix="/api/v1", 
    tags=["shotstack"]
)

# Video expiration management router
app.include_router(
    expiration.router, 
    prefix="/api/v1", 
    tags=["expiration"]
)

# GCP sync fallback router
app.include_router(
    gcp_sync.router, 
    prefix="/api/v1", 
    tags=["gcp-sync"]
)

@app.get("/")
async def root():
    return {"message": "Shotstack Intermediary API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )