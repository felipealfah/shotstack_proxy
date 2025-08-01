from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Dict, Optional
from supabase import create_client, Client
import hashlib
import logging

from ..config import settings

security = HTTPBearer()
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

async def hash_api_key(api_key: str) -> str:
    """Hash API key using SHA-256"""
    return hashlib.sha256(api_key.encode()).hexdigest()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify API key using Supabase database lookup
    """
    try:
        api_key = credentials.credentials
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Hash the provided API key for database lookup
        key_hash = await hash_api_key(api_key)
        
        try:
            # Query API key from Supabase
            response = supabase.table('api_keys').select(
                'id, user_id, name, is_active, last_used_at, users(id, email, token_balance)'
            ).eq('key_hash', key_hash).eq('is_active', True).execute()
            
            if not response.data:
                logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            api_key_record = response.data[0]
            user_data = api_key_record['users']
            
            if not user_data:
                logger.error(f"API key {api_key_record['id']} has no associated user")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key configuration",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update last_used_at timestamp
            try:
                supabase.table('api_keys').update({
                    'last_used_at': 'now()'
                }).eq('id', api_key_record['id']).execute()
            except Exception as e:
                logger.warning(f"Failed to update last_used_at for API key {api_key_record['id']}: {e}")
            
            # Return user information and token balance
            return {
                "user_id": user_data['id'],
                "email": user_data['email'],
                "token_balance": user_data.get('token_balance', 0),
                "api_key_id": api_key_record['id'],
                "api_key_name": api_key_record['name']
            }
            
        except Exception as db_error:
            logger.error(f"Database error during API key validation: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to validate API key - database error"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during API key validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify Supabase JWT token for direct authentication
    """
    try:
        token = credentials.credentials
        
        # Verify JWT token with Supabase
        try:
            response = supabase.auth.get_user(token)
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid JWT token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user = response.user
            
            # Get user data from database
            user_response = supabase.table('users').select(
                'id, email, token_balance'
            ).eq('id', user.id).execute()
            
            if not user_response.data:
                # Create user record if it doesn't exist
                supabase.table('users').insert({
                    'id': user.id,
                    'email': user.email,
                    'token_balance': 0
                }).execute()
                
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'token_balance': 0
                }
            else:
                user_data = user_response.data[0]
            
            return {
                "user_id": user_data['id'],
                "email": user_data['email'],
                "token_balance": user_data.get('token_balance', 0),
                "auth_type": "jwt"
            }
            
        except Exception as jwt_error:
            logger.error(f"JWT validation error: {jwt_error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid JWT token",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during JWT validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Get current user information from API key or JWT token
    Tries API key validation first, then JWT if that fails
    """
    token = credentials.credentials
    
    # Check if it looks like a JWT token (has 3 parts separated by dots)
    if len(token.split('.')) == 3:
        try:
            return await verify_jwt_token(credentials)
        except HTTPException:
            # If JWT fails, try API key validation
            pass
    
    # Default to API key validation
    return await verify_api_key(credentials)