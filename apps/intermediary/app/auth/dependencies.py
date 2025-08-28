"""
Authentication Dependencies for FastAPI
Provides user authentication and authorization utilities
"""

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, Optional
import logging

from app.database.supabase_client import get_supabase_client
from app.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email")
) -> Dict[str, Any]:
    """
    Get current authenticated user from API key and email
    
    Uses the dual authentication system (API Key + Email) to verify
    user identity and return user information.
    
    Args:
        credentials: HTTP Bearer token (API Key)
        x_user_email: User email from X-User-Email header
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        api_key = credentials.credentials
        
        if not x_user_email:
            logger.warning("Authentication attempted without X-User-Email header")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="X-User-Email header is required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        supabase = get_supabase_client()
        
        # Verify API key and email combination
        # Try both api_key and key_hash columns for backward compatibility
        or_condition = f"api_key.eq.{api_key},key_hash.eq.{api_key}"
        api_key_query = supabase.table("api_keys") \
            .select("*") \
            .or_(or_condition) \
            .eq("is_active", True) \
            .execute()
        
        if not api_key_query.data:
            logger.warning("Invalid API key attempted", extra={
                "email": x_user_email,
                "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "short_key"
            })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        api_key_record = api_key_query.data[0]
        user_id = api_key_record["user_id"]
        
        # Get user from auth.users via service role
        # Since profiles table doesn't exist, we'll verify email through Supabase Auth
        try:
            auth_response = supabase.auth.admin.get_user_by_id(user_id)
            if not auth_response.user or auth_response.user.email != x_user_email:
                logger.warning("Email mismatch for API key", extra={
                    "user_id": user_id,
                    "provided_email": x_user_email,
                    "api_key_prefix": api_key[:8] + "..."
                })
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email does not match API key owner",
                    headers={"WWW-Authenticate": "Bearer"}
                )
            user = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name"),
                "created_at": auth_response.user.created_at
            }
        except Exception as auth_error:
            logger.error(f"Failed to verify user: {str(auth_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User verification failed",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        logger.info("User authenticated successfully", extra={
            "user_id": user_id,
            "email": x_user_email,
            "api_key_name": api_key_record.get("name", "unnamed")
        })
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "created_at": user.get("created_at"),
            "api_key_record": api_key_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}", extra={
            "email": x_user_email,
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def get_user_from_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    Alternative authentication method using Supabase JWT tokens
    
    This can be used for frontend authentication where JWT tokens
    are available instead of API keys.
    
    Args:
        token: Supabase JWT token
        
    Returns:
        Dict containing user information
    """
    try:
        supabase = get_supabase_client()
        
        # Verify JWT token with Supabase
        auth_response = supabase.auth.get_user(token)
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired JWT token"
            )
        
        user = auth_response.user
        
        return {
            "id": user.id,
            "email": user.email,
            "name": user.user_metadata.get("name"),
            "created_at": user.created_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"JWT authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT authentication service error"
        )

async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require admin privileges for endpoint access
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    # Check if user has admin role
    # This would need to be implemented based on your user role system
    user_id = current_user["id"]
    
    # Placeholder: implement admin role checking logic
    # For now, we'll check if user is in an admin list or has admin flag
    
    # For now, we'll implement a simple admin check
    # You can extend this by adding an admin table or using user metadata
    supabase = get_supabase_client()
    
    try:
        auth_response = supabase.auth.admin.get_user_by_id(user_id)
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not found"
            )
        
        # Check if user has admin role in metadata (you can customize this)
        user_metadata = auth_response.user.user_metadata or {}
        is_admin = user_metadata.get("role") == "admin" or user_metadata.get("admin", False)
        
    except Exception:
        is_admin = False
    
    if not is_admin:
        logger.warning("Non-admin user attempted admin access", extra={
            "user_id": user_id,
            "email": current_user.get("email")
        })
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    
    return current_user

# Optional: Create dependency for API-only authentication (no email required)
async def get_current_user_api_only(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Alternative authentication for API-only access (backwards compatibility)
    
    This is kept for backwards compatibility with existing API consumers
    that might not have implemented the dual authentication system yet.
    """
    try:
        api_key = credentials.credentials
        
        supabase = get_supabase_client()
        
        or_condition = f"api_key.eq.{api_key},key_hash.eq.{api_key}"
        api_key_query = supabase.table("api_keys") \
            .select("*") \
            .or_(or_condition) \
            .eq("is_active", True) \
            .execute()
        
        if not api_key_query.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        api_key_record = api_key_query.data[0]
        user_id = api_key_record["user_id"]
        
        # Get user from auth.users via service role
        try:
            auth_response = supabase.auth.admin.get_user_by_id(user_id)
            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            user = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "name": auth_response.user.user_metadata.get("name"),
                "created_at": auth_response.user.created_at
            }
        except Exception as auth_error:
            logger.error(f"Failed to get user: {str(auth_error)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User verification failed"
            )
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "created_at": user.get("created_at"),
            "api_key_record": api_key_record
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API-only authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )