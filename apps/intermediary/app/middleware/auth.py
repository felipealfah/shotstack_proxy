from fastapi import HTTPException, Depends, status, Header
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

async def get_email_from_header(x_user_email: str = Header(...)) -> str:
    """Extract email from X-User-Email header"""
    if not x_user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header X-User-Email é obrigatório",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return x_user_email.strip().lower()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify API key using Supabase database lookup
    """
    api_key = credentials.credentials
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    
    try:
        
        try:
            # Use RPC function for validation (like frontend does)
            response = supabase.rpc('validate_api_key', {'api_key': api_key}).execute()
            
            if not response.data or not response.data.get('valid'):
                logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            key_data = response.data
            user_id = key_data['user_id']
            
            # Get user balance from credit_balance table
            balance_response = supabase.table('credit_balance').select('balance').eq('user_id', user_id).execute()
            
            balance = 0
            if balance_response.data:
                balance = balance_response.data[0]['balance']
            
            # Get user email from auth.users (for logging)
            user_email = "unknown"
            try:
                auth_response = supabase.auth.admin.get_user_by_id(user_id)
                if auth_response.user:
                    user_email = auth_response.user.email
            except Exception:
                pass  # Email is not critical, continue without it
            
            # Return user information and token balance
            return {
                "user_id": user_id,
                "email": user_email,
                "token_balance": balance,
                "api_key_id": key_data['key_id'],
                "api_key_name": "API Key"  # We don't get name from RPC, that's ok
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

async def verify_api_key_with_email(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    email: str = Depends(get_email_from_header)
) -> Dict:
    """
    Verify API key AND check if it belongs to the provided email
    Security feature to prevent users from accessing other users' resources
    """
    api_key = credentials.credentials
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # First, validate the API key using the existing RPC function
        response = supabase.rpc('validate_api_key', {'api_key': api_key}).execute()
        
        if not response.data or not response.data.get('valid'):
            logger.warning(f"Invalid API key attempt: {api_key[:10]}... for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        key_data = response.data
        user_id = key_data['user_id']
        
        # Now verify that the API key belongs to the user with the provided email
        try:
            auth_response = supabase.auth.admin.get_user_by_id(user_id)
            if not auth_response.user or not auth_response.user.email:
                logger.error(f"Could not retrieve user email for user_id: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            user_email = auth_response.user.email.strip().lower()
            
            # Check if the email matches
            if user_email != email:
                logger.warning(f"Email mismatch: API key belongs to {user_email}, but request from {email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email não corresponde à API key fornecida",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
        except HTTPException:
            raise
        except Exception as auth_error:
            logger.error(f"Error retrieving user email: {auth_error}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to validate ownership - authentication service error"
            )
        
        # Get user balance from credit_balance table
        balance_response = supabase.table('credit_balance').select('balance').eq('user_id', user_id).execute()
        
        balance = 0
        if balance_response.data:
            balance = balance_response.data[0]['balance']
        
        # Return user information with validated ownership
        return {
            "user_id": user_id,
            "email": user_email,
            "token_balance": balance,
            "api_key_id": key_data['key_id'],
            "api_key_name": "API Key",
            "auth_type": "api_key_with_email"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during dual validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Get current user information from API key or JWT token
    Now supports dual authentication mode for enhanced security
    
    Note: This function is kept for backward compatibility.
    For new endpoints requiring dual auth, use verify_api_key_with_email directly.
    """
    token = credentials.credentials
    
    # Check if it looks like a JWT token (has 3 parts separated by dots)
    if len(token.split('.')) == 3:
        try:
            return await verify_jwt_token(credentials)
        except HTTPException:
            # If JWT fails, try API key validation
            pass
    
    # Default to API key validation (backward compatibility)
    return await verify_api_key(credentials)