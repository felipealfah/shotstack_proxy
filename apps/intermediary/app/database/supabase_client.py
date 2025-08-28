"""
Supabase Client Configuration
Provides centralized Supabase client for database operations
"""

from supabase import create_client, Client
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Global Supabase client instance
_supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance
    
    Returns:
        Supabase client configured with service role key
    """
    global _supabase_client
    
    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise
    
    return _supabase_client

def test_supabase_connection() -> bool:
    """
    Test Supabase database connection
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        supabase = get_supabase_client()
        # Simple test query
        result = supabase.table("profiles").select("id").limit(1).execute()
        logger.info("Supabase connection test successful")
        return True
    except Exception as e:
        logger.error(f"Supabase connection test failed: {str(e)}")
        return False