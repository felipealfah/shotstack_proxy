from typing import Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class UsageService:
    def __init__(self):
        self.supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    
    async def log_render_request(
        self, 
        user_id: str, 
        api_key_id: Optional[str] = None,
        shotstack_job_id: Optional[str] = None,
        status: str = 'pending',
        tokens_consumed: int = 0,
        video_duration_seconds: Optional[int] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Log a render request to the database
        Returns the render request ID
        """
        try:
            render_data = {
                'user_id': user_id,
                'api_key_id': api_key_id,
                'shotstack_job_id': shotstack_job_id,
                'status': status,
                'tokens_consumed': tokens_consumed,
                'video_duration_seconds': video_duration_seconds,
                'request_metadata': metadata or {},
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('render_requests').insert(render_data).execute()
            
            if response.data:
                request_id = response.data[0]['id']
                logger.info(f"Logged render request {request_id} for user {user_id}")
                return request_id
            else:
                logger.error(f"Failed to log render request for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error logging render request: {e}")
            return None
    
    async def update_render_request(
        self, 
        request_id: str, 
        status: str = None,
        tokens_consumed: int = None,
        video_duration_seconds: int = None,
        response_data: Dict[str, Any] = None,
        error_message: str = None
    ) -> bool:
        """
        Update an existing render request
        """
        try:
            update_data = {}
            
            if status:
                update_data['status'] = status
            if tokens_consumed is not None:
                update_data['tokens_consumed'] = tokens_consumed
            if video_duration_seconds is not None:
                update_data['video_duration_seconds'] = video_duration_seconds
            if response_data:
                update_data['response_data'] = response_data
            if error_message:
                update_data['error_message'] = error_message
            
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            response = self.supabase.table('render_requests').update(update_data).eq('id', request_id).execute()
            
            if response.data:
                logger.info(f"Updated render request {request_id}")
                return True
            else:
                logger.error(f"Failed to update render request {request_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating render request {request_id}: {e}")
            return False
    
    async def log_rate_limit_event(
        self,
        user_id: str,
        api_key_id: Optional[str] = None,
        endpoint: str = None,
        exceeded_limit: bool = False,
        current_count: int = 0,
        limit_window: int = 3600
    ) -> bool:
        """
        Log rate limiting events
        """
        try:
            rate_limit_data = {
                'user_id': user_id,
                'api_key_id': api_key_id,
                'endpoint': endpoint,
                'exceeded_limit': exceeded_limit,
                'request_count': current_count,
                'limit_window_seconds': limit_window,
                'created_at': datetime.utcnow().isoformat()
            }
            
            response = self.supabase.table('rate_limit_log').insert(rate_limit_data).execute()
            
            if response.data:
                if exceeded_limit:
                    logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}")
                return True
            else:
                logger.error(f"Failed to log rate limit event for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error logging rate limit event: {e}")
            return False
    
    async def get_user_render_requests(self, user_id: str, limit: int = 100, status: str = None) -> list:
        """
        Get user's render request history
        """
        try:
            query = self.supabase.table('render_requests').select('*').eq('user_id', user_id)
            
            if status:
                query = query.eq('status', status)
            
            response = query.order('created_at', desc=True).limit(limit).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error getting render requests for user {user_id}: {e}")
            return []
    
    async def get_usage_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics for a user
        """
        try:
            from datetime import timedelta
            start_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            response = self.supabase.table('render_requests').select('*').eq(
                'user_id', user_id
            ).gte('created_at', start_date).execute()
            
            requests = response.data or []
            
            total_requests = len(requests)
            successful_requests = len([r for r in requests if r['status'] == 'completed'])
            failed_requests = len([r for r in requests if r['status'] == 'failed'])
            total_tokens = sum(r.get('tokens_consumed', 0) for r in requests)
            total_duration = sum(r.get('video_duration_seconds', 0) for r in requests if r.get('video_duration_seconds'))
            
            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': failed_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'total_tokens_consumed': total_tokens,
                'total_video_duration_seconds': total_duration,
                'average_video_duration': total_duration / total_requests if total_requests > 0 else 0,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats for user {user_id}: {e}")
            return {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'success_rate': 0,
                'total_tokens_consumed': 0,
                'total_video_duration_seconds': 0,
                'average_video_duration': 0,
                'period_days': days
            }