from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Dict
import httpx

from ..config import settings

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify API key with the web service
    """
    try:
        api_key = credentials.credentials
        
        # Try to decode JWT directly first
        try:
            payload = jwt.decode(api_key, settings.JWT_SECRET, algorithms=["HS256"])
            return {
                "user_id": payload.get("user_id"),
                "tokens": payload.get("tokens", 0)
            }
        except JWTError:
            pass  # Continue to web service validation
        
        # Call web service to validate API key
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.WEB_SERVICE_URL}/api/validate-key",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except httpx.RequestError:
        # If web service is unavailable, try JWT bypass
        try:
            payload = jwt.decode(api_key, settings.JWT_SECRET, algorithms=["HS256"])
            return {
                "user_id": payload.get("user_id"),
                "tokens": payload.get("tokens", 0)
            }
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to validate API key - service unavailable"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Get current user information from API key
    """
    return await verify_api_key(credentials)