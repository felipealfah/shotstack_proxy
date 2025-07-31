import httpx
from typing import Optional
from ..config import settings

class TokenService:
    def __init__(self):
        self.web_service_url = settings.WEB_SERVICE_URL
    
    async def get_user_tokens(self, user_id: str) -> int:
        """
        Get user's current token balance from web service
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.web_service_url}/api/users/{user_id}/tokens",
                    timeout=10.0
                )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("tokens", 0)
            else:
                return 0
                
        except httpx.RequestError:
            return 0
    
    async def consume_tokens(self, user_id: str, amount: int) -> bool:
        """
        Consume tokens for a user
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.web_service_url}/api/users/{user_id}/consume-tokens",
                    json={"amount": amount},
                    timeout=10.0
                )
            
            return response.status_code == 200
            
        except httpx.RequestError:
            return False
    
    async def add_tokens(self, user_id: str, amount: int) -> bool:
        """
        Add tokens to a user's balance
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.web_service_url}/api/users/{user_id}/add-tokens",
                    json={"amount": amount},
                    timeout=10.0
                )
            
            return response.status_code == 200
            
        except httpx.RequestError:
            return False