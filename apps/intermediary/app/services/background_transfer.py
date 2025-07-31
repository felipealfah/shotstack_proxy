"""
Serviço para transferência de vídeos em background
"""
import asyncio
import logging
from typing import Dict, Any
from .destination_service import DestinationService

logger = logging.getLogger(__name__)

async def transfer_video_to_gcs_job(ctx, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job em background para transferir vídeo do Shotstack para GCS
    
    Args:
        ctx: ARQ context
        transfer_data: Dados da transferência
        
    Returns:
        Resultado da transferência
    """
    job_id = ctx.get('job_id', 'unknown')
    logger.info(f"Starting background transfer job {job_id}")
    
    try:
        shotstack_url = transfer_data.get('shotstack_url')
        user_id = transfer_data.get('user_id', 'unknown')
        original_job_id = transfer_data.get('original_job_id')
        
        if not shotstack_url or not original_job_id:
            raise ValueError("Missing required transfer data")
        
        # Executar transferência
        destination_service = DestinationService()
        
        logger.info(f"Transferring video for job {original_job_id}")
        gcs_url = await destination_service.transfer_to_gcs(
            shotstack_url, user_id, original_job_id
        )
        
        result = {
            "status": "success",
            "job_id": job_id,
            "original_job_id": original_job_id,
            "gcs_url": gcs_url,
            "shotstack_url": shotstack_url,
            "user_id": user_id,
            "transferred_at": ctx.get('enqueue_time', '').isoformat() if ctx.get('enqueue_time') else None
        }
        
        logger.info(f"Background transfer completed: {gcs_url}")
        return result
        
    except Exception as e:
        logger.error(f"Background transfer failed: {str(e)}")
        return {
            "status": "failed",
            "job_id": job_id,
            "original_job_id": transfer_data.get('original_job_id'),
            "error": str(e),
            "user_id": transfer_data.get('user_id', 'unknown')
        }