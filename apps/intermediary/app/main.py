from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv
from arq import create_pool
from arq.connections import RedisSettings

from .config import settings
from .routers import shotstack, health
from .middleware.auth import verify_api_key
from .middleware.rate_limit import RateLimitMiddleware

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create Redis connection pool
    app.state.redis_pool = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_URL)
    )
    yield
    # Shutdown: Close Redis connection
    await app.state.redis_pool.close()

app = FastAPI(
    title="Shotstack Intermediary API",
    description="Intermediary service for Shotstack video rendering with token-based billing",
    version="1.0.0",
    lifespan=lifespan
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