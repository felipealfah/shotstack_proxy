import httpx
from typing import Dict, Any
from datetime import datetime
from ..config import settings

class UsageService:
    def __init__(self):
        self.web_service_url = settings.WEB_SERVICE_URL
    
    async def log_usage(
        self, 
        user_id: str, 
        action: str, 
        tokens_consumed: int, 
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        Log usage activity to the web service
        """
        try:
            usage_data = {
                "user_id": user_id,
                "action": action,
                "tokens_consumed": tokens_consumed,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.web_service_url}/api/usage/log",
                    json=usage_data,
                    timeout=10.0
                )
            
            return response.status_code == 201
            
        except httpx.RequestError:
            return False
    
    async def get_user_usage(self, user_id: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get user's usage history
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.web_service_url}/api/users/{user_id}/usage",
                    params={"limit": limit},
                    timeout=10.0
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"usage": [], "total": 0}
                
        except httpx.RequestError:
            return {"usage": [], "total": 0}