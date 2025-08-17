"""
Video Expiration Management Router
Provides endpoints for monitoring and managing video expiration.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging

from ..services.expiration_service import expiration_service, run_expiration_sync, get_stats
from ..middleware.auth import verify_api_key, verify_api_key_with_email
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/expiration/stats")
async def get_expiration_stats(
    current_user: dict = Depends(verify_api_key_with_email)
) -> Dict[str, Any]:
    """
    Get video expiration statistics for the current user.
    Returns counts of total, expired, and soon-to-expire videos.
    """
    try:
        stats = await get_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Error getting expiration stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving expiration statistics: {str(e)}"
        )

@router.post("/expiration/sync")
async def trigger_expiration_sync(
    current_user: dict = Depends(verify_api_key_with_email)
) -> Dict[str, Any]:
    """
    Manually trigger expiration sync process.
    Useful for testing or immediate sync needs.
    """
    try:
        result = await run_expiration_sync()
        return {
            "success": True,
            "message": "Expiration sync completed",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error in manual expiration sync: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running expiration sync: {str(e)}"
        )

@router.get("/expiration/user-videos")
async def get_user_video_status(
    current_user: dict = Depends(verify_api_key_with_email)
) -> Dict[str, Any]:
    """
    Get detailed video status for the current user including expiration info.
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="User ID not found in authentication context"
            )
        
        # Get user's videos with expiration status
        result = expiration_service.supabase.table('renders').select(
            'id, job_id, project_name, video_url, status, created_at, expires_at, is_expired'
        ).eq('user_id', user_id).order('created_at', desc=True).limit(settings.USER_VIDEOS_PAGE_LIMIT).execute()
        
        videos = []
        for video in result.data or []:
            # Calculate hours remaining
            from datetime import datetime
            if video['expires_at'] and not video['is_expired']:
                expires_at = datetime.fromisoformat(video['expires_at'].replace('Z', '+00:00'))
                now = datetime.now(expires_at.tzinfo)
                hours_remaining = max(0, int((expires_at - now).total_seconds() / 3600))
            else:
                hours_remaining = 0
            
            videos.append({
                **video,
                'hours_remaining': hours_remaining,
                'status_label': get_status_label(video['is_expired'], hours_remaining)
            })
        
        return {
            "success": True,
            "data": {
                "videos": videos,
                "total_count": len(videos)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user video status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user video status: {str(e)}"
        )

def get_status_label(is_expired: bool, hours_remaining: int) -> str:
    """Generate user-friendly status label for videos."""
    if is_expired:
        return "Expirado"
    elif hours_remaining <= 6:
        return "Expirando em breve"
    elif hours_remaining <= 24:
        return "Expira em 1 dia"
    else:
        return "Disponível"