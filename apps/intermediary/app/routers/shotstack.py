from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uuid
import json
import asyncio
import logging
from datetime import datetime

from ..config import settings
from ..services.token_service import TokenService
from ..services.usage_service import UsageService
from ..services.destination_service import DestinationService
from ..middleware.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

class RenderRequest(BaseModel):
    timeline: Dict[str, Any]
    output: Dict[str, Any]
    destinations: Optional[List[Dict[str, Any]]] = None
    webhook: Optional[str] = None

class RenderResponse(BaseModel):
    success: bool
    message: str
    job_id: str
    estimated_tokens: int = 1
    
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class VideoLinksResponse(BaseModel):
    success: bool
    message: str
    video_url: Optional[str] = None
    poster_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    render_id: Optional[str] = None
    transfer_status: Optional[str] = None  # "completed", "in_progress", "pending"

class TransferStatusResponse(BaseModel):
    success: bool
    message: str
    transfer_status: str  # "completed", "in_progress", "pending", "failed"
    video_url: Optional[str] = None
    job_id: str


@router.post("/render", response_model=RenderResponse)
async def create_render(
    render_request: RenderRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Queue render requests for processing by workers
    """
    try:
        user_id = current_user["user_id"]
        
        # Check if user has enough tokens
        token_service = TokenService()
        user_tokens = await token_service.get_user_tokens(user_id)
        
        # Calculate tokens needed (simplified - 1 token per render for now)
        tokens_needed = 1
        
        if user_tokens < tokens_needed:
            raise HTTPException(
                status_code=402, 
                detail="Insufficient tokens. Please purchase more tokens."
            )
        
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Configurar destinos automaticamente (Google Cloud Storage)
        destination_service = DestinationService()
        
        # Configurar destinations no output
        output_config = render_request.output.copy()
        
        # Se o usuário não forneceu destinos customizados, usar os padrões
        if not render_request.destinations:
            destinations = destination_service.get_default_destinations(user_id, job_id)
            logger.info(f"Using default destinations for job {job_id}: GCS + Shotstack CDN")
        else:
            # Usar destinos fornecidos pelo usuário, mas adicionar GCS se não estiver presente
            destinations = render_request.destinations.copy()
            has_gcs = any(dest.get("provider") == "googlecloudstorage" for dest in destinations)
            
            if not has_gcs:
                gcs_destinations = destination_service.get_default_destinations(user_id, job_id)
                destinations.extend([dest for dest in gcs_destinations if dest.get("provider") == "googlecloudstorage"])
                logger.info(f"Added GCS destination to user-provided destinations for job {job_id}")
        
        # Adicionar destinations ao output (não no payload raiz)
        output_config["destinations"] = destinations
        
        # Prepare job data for worker
        job_data = {
            "user_id": user_id,
            "timeline": render_request.timeline,
            "output": output_config,  # Output já com destinations incluídas
            "webhook": render_request.webhook,
            "tokens_consumed": tokens_needed,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Get Redis pool from app state
        redis_pool = request.app.state.redis_pool
        
        # Enqueue job for worker processing
        job = await redis_pool.enqueue_job(
            "render_video_job",
            job_data,
            _job_id=job_id
        )
        
        # Consume tokens immediately (since job is queued)
        await token_service.consume_tokens(user_id, tokens_needed)
        
        # Log usage
        background_tasks.add_task(
            log_usage, 
            user_id, 
            "render_queued", 
            tokens_needed, 
            {"job_id": job_id}
        )
        
        return RenderResponse(
            success=True,
            message="Render job queued successfully",
            job_id=job_id,
            estimated_tokens=tokens_needed
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get job status from Redis queue
    """
    try:
        # Get Redis pool from app state
        redis_pool = request.app.state.redis_pool
        
        # Get job from Redis using correct arq API
        from arq.jobs import Job
        job = Job(job_id, redis_pool)
        
        # Get job status and result
        status = await job.status()
        result = await job.result()
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )
        
        return JobStatusResponse(
            job_id=job_id,
            status=status.value if status else "unknown",
            result=result if isinstance(result, dict) else None,
            error=result.get("error") if isinstance(result, dict) and result.get("status") == "failed" else None
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/render/{render_id}")
async def get_shotstack_render_status(
    render_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Check Shotstack render status directly (for completed jobs)
    """
    try:
        # Get Redis pool from app state
        redis_pool = request.app.state.redis_pool
        
        # Enqueue status check job
        job = await redis_pool.enqueue_job(
            "check_render_status_job",
            render_id
        )
        
        # Wait a bit for the job to complete (quick status check)
        await asyncio.sleep(1)
        
        result = await job.result()
        
        if result and result.get("status") == "success":
            return result.get("data", {})
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to check render status")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/videos/{job_id}", response_model=VideoLinksResponse)
async def get_video_links(
    job_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get video download links from completed Shotstack render
    """
    try:
        # Get Redis pool from app state
        redis_pool = request.app.state.redis_pool
        
        # Get job from Redis using correct arq API
        from arq.jobs import Job
        job = Job(job_id, redis_pool)
        
        # Get job status and result
        status = await job.status()
        result = await job.result()
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail="Job not found"
            )
        
        # Check if job is completed
        if status.value != "complete":
            return VideoLinksResponse(
                success=False,
                message=f"Job status: {status.value}. Video not ready yet.",
                job_id=job_id
            )
        
        # Check if job failed
        if result and result.get("status") == "failed":
            return VideoLinksResponse(
                success=False,
                message=f"Video rendering failed: {result.get('error', 'Unknown error')}",
                job_id=job_id
            )
        
        # Check if job succeeded and has Shotstack render_id
        if result and result.get("status") == "success":
            shotstack_render_id = result.get("shotstack_render_id")
            
            if not shotstack_render_id:
                return VideoLinksResponse(
                    success=False,
                    message="No Shotstack render ID found"
                )
            
            # Query Shotstack API directly for final video links
            import httpx
            from ..config import settings
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.SHOTSTACK_API_URL}/render/{shotstack_render_id}",
                        headers={
                            "x-api-key": settings.SHOTSTACK_API_KEY,
                            "Content-Type": "application/json"
                        },
                        timeout=10.0
                    )
                
                if response.status_code == 200:
                    shotstack_data = response.json().get("response", {})
                    
                    # Log the full response for debugging custom destinations
                    logger.info(f"Shotstack response for render {shotstack_render_id}: {shotstack_data}")
                    
                    # Verificar se já existe transferência em andamento ou concluída
                    destination_service = DestinationService()
                    shotstack_url = shotstack_data.get("url")
                    
                    # Obter user_id do job original
                    from arq.jobs import Job
                    user_id = "unknown"
                    
                    try:
                        original_job = Job(job_id, redis_pool)
                        original_result = await original_job.result()
                        
                        if (original_result and isinstance(original_result, dict)):
                            user_id = original_result.get("user_id", "unknown")
                            
                    except Exception as e:
                        logger.error(f"Failed to get original job data: {str(e)}")
                        # Usar user_id padrão se não conseguir obter do job
                    
                    if shotstack_url:
                        # Primeiro, verificar se o arquivo já existe no GCS
                        gcs_path = destination_service._generate_gcs_path(user_id, job_id)
                        video_url = destination_service.get_gcs_public_url(gcs_path)
                        
                        # Verificar se arquivo existe no GCS
                        import httpx
                        try:
                            async with httpx.AsyncClient(timeout=5.0) as client:
                                gcs_check = await client.head(video_url)
                                if gcs_check.status_code == 200:
                                    logger.info(f"Video already exists in GCS: {video_url}")
                                else:
                                    raise httpx.HTTPStatusError("File not found", request=None, response=gcs_check)
                        except:
                            # Arquivo não existe no GCS, iniciar transferência em background
                            logger.info(f"Starting background transfer for render {shotstack_render_id}")
                            
                            transfer_data = {
                                "shotstack_url": shotstack_url,
                                "user_id": user_id,
                                "original_job_id": job_id
                            }
                            
                            # Enfileirar transferência em background
                            transfer_job = await redis_pool.enqueue_job(
                                "transfer_video_to_gcs_job",
                                transfer_data,
                                _job_id=f"transfer_{job_id}"
                            )
                            
                            logger.info(f"Background transfer queued: {transfer_job.job_id}")
                            
                            # Retornar URL do GCS (mesmo que ainda não exista)
                            # O arquivo estará disponível em breve
                        
                    else:
                        logger.error(f"No Shotstack URL found in response for render {shotstack_render_id}")
                        gcs_path = destination_service._generate_gcs_path(user_id, job_id)
                        video_url = destination_service.get_gcs_public_url(gcs_path)
                    
                    # URLs de poster e thumbnail (ficam no Shotstack CDN)
                    poster_url = shotstack_data.get("poster")
                    thumbnail_url = shotstack_data.get("thumbnail")
                    
                    # Verificar status da transferência
                    transfer_status = "completed"
                    try:
                        async with httpx.AsyncClient(timeout=3.0) as client:
                            gcs_check = await client.head(video_url)
                            if gcs_check.status_code != 200:
                                transfer_status = "in_progress"
                    except:
                        transfer_status = "in_progress"
                    
                    return VideoLinksResponse(
                        success=True,
                        message="Video rendered successfully",
                        video_url=video_url,
                        poster_url=poster_url,
                        thumbnail_url=thumbnail_url,
                        render_id=shotstack_render_id,
                        transfer_status=transfer_status
                    )
                else:
                    return VideoLinksResponse(
                        success=False,
                        message=f"Failed to fetch video from Shotstack: {response.status_code}"
                    )
                    
            except Exception as e:
                return VideoLinksResponse(
                    success=False,
                    message=f"Error querying Shotstack: {str(e)}"
                )
        
        # If we get here, something is wrong with the result format
        return VideoLinksResponse(
            success=False,
            message="Unexpected job result format",
            job_id=job_id
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@router.post("/webhook")
async def shotstack_webhook(request: Request):
    """
    Handle webhooks from Shotstack
    """
    try:
        body = await request.body()
        webhook_data = json.loads(body)
        
        # Process webhook data
        # Log completion, update status, etc.
        
        return {"status": "received"}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Webhook processing error: {str(e)}"
        )


async def log_usage(user_id: str, action: str, tokens_consumed: int, response_data: Dict):
    """
    Background task to log usage
    """
    try:
        usage_service = UsageService()
        await usage_service.log_usage(user_id, action, tokens_consumed, response_data)
    except Exception as e:
        print(f"Error logging usage: {str(e)}")