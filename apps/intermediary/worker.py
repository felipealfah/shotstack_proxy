"""
ARQ Worker for processing Shotstack render jobs
Processes jobs from Redis queue and calls Shotstack API
"""
import httpx
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from arq import create_pool
from arq.connections import RedisSettings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def render_video_job(ctx, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a video render job by calling Shotstack API
    
    Args:
        ctx: ARQ context with job info
        job_data: Dictionary containing render parameters
    
    Returns:
        Dict with render result or error info
    """
    job_id = ctx['job_id']
    logger.info(f"Processing render job {job_id}")
    
    try:
        # Extract render data
        timeline = job_data.get('timeline')
        output = job_data.get('output')
        webhook = job_data.get('webhook')
        user_id = job_data.get('user_id', 'unknown')
        
        if not timeline or not output:
            raise ValueError("Missing required fields: timeline or output")
        
        # Prepare Shotstack request
        shotstack_payload = {
            "timeline": timeline,
            "output": output  # Output já contém destinations
        }
            
        if webhook:
            shotstack_payload["webhook"] = webhook
        
        # Log destinations if present in output
        if output.get("destinations"):
            logger.info(f"Destinations found in output: {output['destinations']}")
        else:
            logger.warning(f"No destinations found in output for job {job_id}")
        
        # Log the complete payload being sent to Shotstack
        logger.info(f"Complete Shotstack payload for job {job_id}: {shotstack_payload}")
        
        # Make request to Shotstack API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{os.getenv('SHOTSTACK_API_URL', 'https://api.shotstack.io/v1')}/render",
                headers={
                    "x-api-key": os.getenv("SHOTSTACK_API_KEY"),
                    "Content-Type": "application/json"
                },
                json=shotstack_payload
            )
        
        # Process response
        if response.status_code == 201:
            shotstack_response = response.json()
            render_id = shotstack_response.get('response', {}).get('id')
            
            result = {
                "status": "success",
                "job_id": job_id,
                "user_id": user_id,
                "shotstack_render_id": render_id,
                "shotstack_response": shotstack_response,
                "processed_at": datetime.utcnow().isoformat(),
                "tokens_consumed": job_data.get('tokens_consumed', 1)
            }
            
            logger.info(f"Job {job_id} completed successfully. Render ID: {render_id}")
            return result
            
        else:
            # Shotstack API error
            error_detail = response.text
            logger.error(f"Job {job_id} failed with Shotstack error: {response.status_code} - {error_detail}")
            
            return {
                "status": "failed",
                "job_id": job_id,
                "user_id": user_id,
                "error": f"Shotstack API error: {response.status_code}",
                "error_detail": error_detail,
                "processed_at": datetime.utcnow().isoformat()
            }
            
    except httpx.TimeoutException:
        logger.error(f"Job {job_id} timed out")
        return {
            "status": "failed",
            "job_id": job_id,
            "user_id": user_id,
            "error": "Request timeout",
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

async def check_render_status_job(ctx, render_id: str) -> Dict[str, Any]:
    """
    Check the status of a render job on Shotstack
    
    Args:
        ctx: ARQ context
        render_id: Shotstack render ID
    
    Returns:
        Dict with render status
    """
    job_id = ctx['job_id']
    logger.info(f"Checking render status for {render_id} (job {job_id})")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{os.getenv('SHOTSTACK_API_URL', 'https://api.shotstack.io/v1')}/render/{render_id}",
                headers={
                    "x-api-key": os.getenv("SHOTSTACK_API_KEY")
                }
            )
        
        if response.status_code == 200:
            return {
                "status": "success",
                "job_id": job_id,
                "render_id": render_id,
                "data": response.json(),
                "checked_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "failed",
                "job_id": job_id,
                "render_id": render_id,
                "error": f"Shotstack API error: {response.status_code}",
                "error_detail": response.text,
                "checked_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Failed to check render status for {render_id}: {str(e)}")
        return {
            "status": "failed",
            "job_id": job_id,
            "render_id": render_id,
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }

async def startup(ctx):
    """Worker startup function"""
    logger.info("Worker starting up...")

async def shutdown(ctx):
    """Worker shutdown function"""
    logger.info("Worker shutting down...")

# ARQ Worker Settings
class WorkerSettings:
    from app.services.background_transfer import transfer_video_to_gcs_job
    functions = [render_video_job, check_render_status_job, transfer_video_to_gcs_job]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    
    # Worker configuration
    max_jobs = 10  # Process up to 10 jobs concurrently
    job_timeout = 300  # 5 minutes timeout per job
    keep_result = 3600  # Keep results for 1 hour
    
    # Retry configuration
    max_tries = 3
    retry_jobs = True
    
    # Startup/shutdown hooks
    on_startup = startup
    on_shutdown = shutdown

if __name__ == "__main__":
    # Run worker directly
    import arq
    arq.run_worker(WorkerSettings)