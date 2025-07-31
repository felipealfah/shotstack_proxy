from fastapi import APIRouter
from pydantic import BaseModel
import redis
from ..config import settings

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    redis: str
    shotstack_config: str

@router.get("/", response_model=HealthResponse)
async def health_check():
    health_status = {
        "status": "healthy",
        "redis": "unknown", 
        "shotstack_config": "unknown"
    }
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "healthy"
    except Exception:
        health_status["redis"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check Shotstack config
    if settings.SHOTSTACK_API_KEY and settings.SHOTSTACK_API_URL:
        health_status["shotstack_config"] = "configured"
    else:
        health_status["shotstack_config"] = "missing"
        health_status["status"] = "unhealthy"
    
    return health_status