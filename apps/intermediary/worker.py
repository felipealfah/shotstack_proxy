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

async def refund_tokens_for_failed_job(user_id: str, tokens_amount: int, job_id: str) -> bool:
    """
    Reembolsa tokens quando um job falha
    """
    try:
        # Importar TokenService localmente para evitar import circular
        from app.services.token_service import TokenService
        
        token_service = TokenService()
        success = await token_service.add_tokens(
            user_id=user_id,
            amount=tokens_amount,
            description=f"Reembolso automático - Job {job_id} falhou",
            transaction_type="refund"
        )
        
        if success:
            logger.info(f"Successfully refunded {tokens_amount} tokens to user {user_id} for failed job {job_id}")
        else:
            logger.error(f"Failed to refund {tokens_amount} tokens to user {user_id} for failed job {job_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error refunding tokens for user {user_id}, job {job_id}: {str(e)}")
        return False

def clean_shotstack_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean payload para remover propriedades inválidas do Shotstack
    Remove 'source' de assets quando 'src' está presente
    """
    def clean_asset(asset):
        if isinstance(asset, dict) and 'source' in asset and 'src' in asset:
            # Remover 'source' se 'src' estiver presente
            cleaned = asset.copy()
            cleaned.pop('source', None)
            logger.info(f"Removed 'source' property from asset: {asset.get('type', 'unknown')}")
            return cleaned
        return asset
    
    def clean_clips(clips):
        if not isinstance(clips, list):
            return clips
        
        cleaned_clips = []
        for clip in clips:
            if isinstance(clip, dict) and 'asset' in clip:
                cleaned_clip = clip.copy()
                cleaned_clip['asset'] = clean_asset(clip['asset'])
                cleaned_clips.append(cleaned_clip)
            else:
                cleaned_clips.append(clip)
        return cleaned_clips
    
    def clean_tracks(tracks):
        if not isinstance(tracks, list):
            return tracks
        
        cleaned_tracks = []
        for track in tracks:
            if isinstance(track, dict) and 'clips' in track:
                cleaned_track = track.copy()
                cleaned_track['clips'] = clean_clips(track['clips'])
                cleaned_tracks.append(cleaned_track)
            else:
                cleaned_tracks.append(track)
        return cleaned_tracks
    
    # Limpar o payload
    cleaned_payload = payload.copy()
    
    if 'timeline' in cleaned_payload and isinstance(cleaned_payload['timeline'], dict):
        timeline = cleaned_payload['timeline'].copy()
        if 'tracks' in timeline:
            timeline['tracks'] = clean_tracks(timeline['tracks'])
        cleaned_payload['timeline'] = timeline
    
    return cleaned_payload

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
        
        # ✅ LIMPAR PAYLOAD: Remover propriedades inválidas do Shotstack
        shotstack_payload = clean_shotstack_payload(shotstack_payload)
        
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
            
            # ✅ SINCRONIZAR STATUS COM SUPABASE
            try:
                from app.services.usage_service import UsageService
                usage_service = UsageService()
                await usage_service.update_render_request(
                    job_id=job_id,
                    status='completed',
                    shotstack_render_id=render_id
                )
                logger.info(f"Updated Supabase status to 'completed' for job {job_id}")
            except Exception as sync_error:
                logger.error(f"Failed to sync Supabase status for job {job_id}: {sync_error}")
            
            logger.info(f"Job {job_id} completed successfully. Render ID: {render_id}")
            
            # ✅ NOVA FUNCIONALIDADE: Enfileirar transferência automática
            try:
                # Obter pool Redis para agendar auto-transferência
                from arq import create_pool
                redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
                pool = await create_pool(redis_settings)
                
                transfer_data = {
                    "shotstack_render_id": render_id,
                    "user_id": user_id,
                    "original_job_id": job_id,
                    "created_at": datetime.utcnow().isoformat()
                }
                
                # Agendar para verificar em 30 segundos (tempo mínimo de render)
                await pool.enqueue_job(
                    "auto_transfer_when_ready_job",
                    transfer_data,
                    _job_id=f"auto_transfer_{job_id}",
                    _defer_by=30  # Esperar 30s antes de começar a verificar
                )
                
                await pool.close()
                logger.info(f"🚀 AUTO-TRANSFER SCHEDULED: Will check render {render_id} in 30s")
                
            except Exception as auto_transfer_error:
                logger.error(f"Failed to schedule auto-transfer for job {job_id}: {auto_transfer_error}")
                # Não falhar o job principal por causa disso
            
            return result
            
        else:
            # Shotstack API error - REEMBOLSAR TOKENS
            error_detail = response.text
            logger.error(f"Job {job_id} failed with Shotstack error: {response.status_code} - {error_detail}")
            
            # ✅ REEMBOLSO AUTOMÁTICO: Quando job falha, devolver tokens
            tokens_to_refund = job_data.get('tokens_consumed', 1)
            refund_success = await refund_tokens_for_failed_job(user_id, tokens_to_refund, job_id)
            
            # ✅ SINCRONIZAR STATUS COM SUPABASE
            try:
                from app.services.usage_service import UsageService
                usage_service = UsageService()
                await usage_service.update_render_request(
                    job_id=job_id,
                    status='failed',
                    error_message=f"Shotstack API error: {response.status_code} - {error_detail}"
                )
                logger.info(f"Updated Supabase status to 'failed' for job {job_id}")
            except Exception as sync_error:
                logger.error(f"Failed to sync Supabase status for job {job_id}: {sync_error}")
            
            return {
                "status": "failed",
                "job_id": job_id,
                "user_id": user_id,
                "error": f"Shotstack API error: {response.status_code}",
                "error_detail": error_detail,
                "processed_at": datetime.utcnow().isoformat(),
                "tokens_refunded": tokens_to_refund if refund_success else 0,
                "refund_status": "success" if refund_success else "failed"
            }
            
    except httpx.TimeoutException:
        logger.error(f"Job {job_id} timed out")
        
        # ✅ REEMBOLSO AUTOMÁTICO: Timeout também deve reembolsar
        tokens_to_refund = job_data.get('tokens_consumed', 1)
        refund_success = await refund_tokens_for_failed_job(user_id, tokens_to_refund, job_id)
        
        # ✅ SINCRONIZAR STATUS COM SUPABASE
        try:
            from app.services.usage_service import UsageService
            usage_service = UsageService()
            await usage_service.update_render_request(
                job_id=job_id,
                status='failed',
                error_message="Request timeout"
            )
            logger.info(f"Updated Supabase status to 'failed' (timeout) for job {job_id}")
        except Exception as sync_error:
            logger.error(f"Failed to sync Supabase status for job {job_id}: {sync_error}")
        
        return {
            "status": "failed",
            "job_id": job_id,
            "user_id": user_id,
            "error": "Request timeout",
            "processed_at": datetime.utcnow().isoformat(),
            "tokens_refunded": tokens_to_refund if refund_success else 0,
            "refund_status": "success" if refund_success else "failed"
        }
        
    except Exception as e:
        logger.error(f"Job {job_id} failed with error: {str(e)}")
        
        # ✅ REEMBOLSO AUTOMÁTICO: Qualquer exception deve reembolsar
        tokens_to_refund = job_data.get('tokens_consumed', 1)
        refund_success = await refund_tokens_for_failed_job(user_id, tokens_to_refund, job_id)
        
        # ✅ SINCRONIZAR STATUS COM SUPABASE
        try:
            from app.services.usage_service import UsageService
            usage_service = UsageService()
            await usage_service.update_render_request(
                job_id=job_id,
                status='failed',
                error_message=str(e)
            )
            logger.info(f"Updated Supabase status to 'failed' (exception) for job {job_id}")
        except Exception as sync_error:
            logger.error(f"Failed to sync Supabase status for job {job_id}: {sync_error}")
        
        return {
            "status": "failed",
            "job_id": job_id,
            "user_id": user_id,
            "error": str(e),
            "processed_at": datetime.utcnow().isoformat(),
            "tokens_refunded": tokens_to_refund if refund_success else 0,
            "refund_status": "success" if refund_success else "failed"
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
    from app.services.background_transfer import transfer_video_to_gcs_job, ensure_video_transferred_job, auto_transfer_when_ready_job
    functions = [render_video_job, check_render_status_job, transfer_video_to_gcs_job, ensure_video_transferred_job, auto_transfer_when_ready_job]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    )
    
    # Worker configuration for scalable high concurrency
    max_jobs = int(os.getenv("ARQ_MAX_JOBS", "50"))  # Default 50, configurable via env (30/50/100+)
    job_timeout = int(os.getenv("ARQ_JOB_TIMEOUT", "300"))  # 5 minutes timeout per job
    keep_result = int(os.getenv("ARQ_KEEP_RESULT", "7200"))  # Keep results for 2 hours (increased for high volume)
    
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