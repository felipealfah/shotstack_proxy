from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import time
import json
from typing import Optional

from ..config import settings

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = redis.from_url(settings.REDIS_URL)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        # Get API key from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return await call_next(request)
        
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        # Check rate limit
        if await self._is_rate_limited(api_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        return await call_next(request)
    
    async def _is_rate_limited(self, api_key: str) -> bool:
        """
        Check if API key has exceeded rate limit
        """
        try:
            key = f"rate_limit:{api_key}"
            current_time = int(time.time())
            window_start = current_time - settings.RATE_LIMIT_WINDOW
            
            # Remove old entries
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_requests = self.redis_client.zcard(key)
            
            if current_requests >= settings.RATE_LIMIT_REQUESTS:
                return True
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            self.redis_client.expire(key, settings.RATE_LIMIT_WINDOW)
            
            return False
            
        except redis.RedisError:
            # If Redis is down, allow the request
            return False