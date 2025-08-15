"""
Simple ARQ Worker for Shotstack renders - Clean version
"""
import httpx
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from arq.connections import RedisSettings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def render_video_job(ctx, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple render job processor
    """
    job_id = ctx['job_id']
    logger.info(f"Processing render job {job_id}")
    
    try:
        # Extract basic data
        timeline = job_data.get('timeline')
        output = job_data.get('output')
        user_id = job_data.get('user_id', 'unknown')
        
        if not timeline or not output:
            raise ValueError("Missing timeline or output")
        
        # Prepare payload
        payload = {
            "timeline": timeline,
            "output": output
        }
        
        logger.info(f"Sending payload to Shotstack for job {job_id}")
        
        # Get environment variables safely
        api_url = os.getenv('SHOTSTACK_API_URL', 'https://api.shotstack.io/v1')
        api_key = os.getenv('SHOTSTACK_API_KEY')
        
        # Make API call
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_url}/render",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json"
                },
                json=payload
            )
        
        if response.status_code == 201:
            shotstack_response = response.json()
            render_id = shotstack_response.get('response', {}).get('id')
            
            logger.info(f"Job {job_id} completed successfully. Render ID: {render_id}")
            
            return {
                "status": "success",
                "job_id": job_id,
                "user_id": user_id,
                "shotstack_render_id": render_id,
                "shotstack_response": shotstack_response,
                "processed_at": datetime.utcnow().isoformat(),
                "tokens_consumed": job_data.get('tokens_consumed', 1)
            }
        else:
            error_detail = response.text
            logger.error(f"Job {job_id} failed: {response.status_code} - {error_detail}")
            
            return {
                "status": "failed",
                "job_id": job_id,
                "user_id": user_id,
                "error": f"Shotstack API error: {response.status_code}",
                "error_detail": error_detail,
                "processed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}")
        return {
            "status": "failed",
            "job_id": job_id,
            "user_id": user_id,
            "error": str(e),
            "processed_at": datetime.utcnow().isoformat()
        }

async def startup(ctx):
    """Worker startup"""
    logger.info("Worker starting up...")

async def shutdown(ctx):
    """Worker shutdown"""
    logger.info("Worker shutting down...")

# Worker Settings
class WorkerSettings:
    functions = [render_video_job]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    
    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    max_tries = 3
    retry_jobs = True
    
    on_startup = startup
    on_shutdown = shutdown

if __name__ == "__main__":
    import arq
    arq.run_worker(WorkerSettings)