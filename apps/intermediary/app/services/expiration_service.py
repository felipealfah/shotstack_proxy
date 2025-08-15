"""
Video Expiration Service
Handles synchronization of video expiration status with GCS lifecycle policy.
GCS Policy: Delete objects after configurable retention period (default: 2 days from creation).
Retention period configurable via VIDEO_RETENTION_DAYS environment variable.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

class ExpirationService:
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    
    async def mark_expired_videos(self) -> Dict[str, Any]:
        """
        Mark videos as expired when they exceed 2 days retention period.
        This syncs with GCS lifecycle policy that deletes objects after 2 days.
        """
        try:
            logger.info("Starting expired videos sync job...")
            
            # Calculate cutoff timestamp (configurable retention period)
            cutoff_time = datetime.now() - timedelta(days=settings.VIDEO_RETENTION_DAYS)
            
            # Mark videos as expired in database
            result = self.supabase.table('renders').update({
                'is_expired': True
            }).lt('created_at', cutoff_time.isoformat()).eq('is_expired', False).execute()
            
            expired_count = len(result.data) if result.data else 0
            
            logger.info(f"Marked {expired_count} videos as expired (older than {cutoff_time}) - retention: {settings.VIDEO_RETENTION_DAYS} days")
            
            return {
                "success": True,
                "expired_count": expired_count,
                "cutoff_time": cutoff_time.isoformat(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error marking expired videos: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_expiration_stats(self) -> Dict[str, Any]:
        """Get statistics about video expiration status."""
        try:
            # Count total videos
            total_result = self.supabase.table('renders').select('id', count='exact').execute()
            total_videos = total_result.count or 0
            
            # Count expired videos
            expired_result = self.supabase.table('renders').select('id', count='exact').eq('is_expired', True).execute()
            expired_videos = expired_result.count or 0
            
            # Count videos expiring in next 24h
            tomorrow = datetime.now() + timedelta(hours=24)
            expiring_soon_result = self.supabase.table('renders').select('id', count='exact').lt('expires_at', tomorrow.isoformat()).eq('is_expired', False).execute()
            expiring_soon = expiring_soon_result.count or 0
            
            return {
                "total_videos": total_videos,
                "expired_videos": expired_videos,
                "active_videos": total_videos - expired_videos,
                "expiring_in_24h": expiring_soon,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting expiration stats: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def cleanup_expired_records(self, days_old: int = None) -> Dict[str, Any]:
        """
        Optional: Clean up very old expired video records from database.
        Only removes records, not the actual video files (GCS handles that).
        """
        try:
            # Use configured cleanup days if not specified
            cleanup_days = days_old if days_old is not None else settings.DB_RECORD_CLEANUP_DAYS
            cutoff_time = datetime.now() - timedelta(days=cleanup_days)
            
            # Delete very old expired records
            result = self.supabase.table('renders').delete().eq('is_expired', True).lt('created_at', cutoff_time.isoformat()).execute()
            
            deleted_count = len(result.data) if result.data else 0
            
            logger.info(f"Cleaned up {deleted_count} old expired records (older than {cleanup_days} days)")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_days": cleanup_days,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up expired records: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global instance
expiration_service = ExpirationService()

# Convenience functions for cron jobs
async def run_expiration_sync():
    """Main function called by cron scheduler."""
    return await expiration_service.mark_expired_videos()

async def run_cleanup():
    """Cleanup function called by cron scheduler."""
    return await expiration_service.cleanup_expired_records()

async def get_stats():
    """Get expiration statistics."""
    return await expiration_service.get_expiration_stats()