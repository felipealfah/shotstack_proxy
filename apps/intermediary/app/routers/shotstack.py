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

class BatchRenderRequest(BaseModel):
    renders: Optional[List[RenderRequest]] = None
    batch_name: Optional[str] = None
    
    # Accept direct array format from n8n
    def __init__(self, **data):
        # Handle direct array input from n8n
        if isinstance(data, list):
            # N8N sends array directly
            renders_data = []
            for item in data:
                renders_data.append(RenderRequest(**item))
            super().__init__(renders=renders_data)
        elif 'renders' not in data and len(data) == 1:
            # Check if the data is a single key with array value
            first_key = list(data.keys())[0]
            first_value = data[first_key]
            if isinstance(first_value, list):
                renders_data = []
                for item in first_value:
                    renders_data.append(RenderRequest(**item))
                super().__init__(renders=renders_data)
            else:
                super().__init__(**data)
        else:
            super().__init__(**data)

class BatchRenderResponse(BaseModel):
    success: bool
    message: str
    batch_id: str
    total_jobs: int
    job_ids: List[str]
    estimated_tokens_total: int


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
        
        # Log render request in Supabase with job_id correlation
        usage_service = UsageService()
        render_request_id = await usage_service.log_render_request(
            user_id=user_id,
            job_id=job_id,
            status='queued',
            tokens_consumed=tokens_needed,
            metadata={"api_request": True}
        )
        
        logger.info(f"Logged render request {render_request_id} for job {job_id}")
        
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
        
        # Try to get job result directly from Redis
        try:
            # Check if the job result exists in Redis
            result_key = f"arq:result:{job_id}"
            redis_client = redis_pool
            raw_result = await redis_client.get(result_key)
            
            if raw_result is None:
                # Job not found or expired
                return JobStatusResponse(
                    job_id=job_id,
                    status="not_found",
                    result=None,
                    error="Job not found or expired"
                )
            
            # Try to deserialize the result
            import pickle
            result_data = pickle.loads(raw_result)
            
            # Extract job result
            job_result = result_data.get('r', {})
            
            # Determine status based on result
            if isinstance(job_result, dict):
                job_status = job_result.get('status', 'completed')
                if job_status == 'success':
                    status = 'completed'
                elif job_status == 'failed':
                    status = 'failed'
                else:
                    status = job_status
            else:
                status = 'completed'
            
            return JobStatusResponse(
                job_id=job_id,
                status=status,
                result=job_result if isinstance(job_result, dict) else {"data": job_result},
                error=job_result.get("error") if isinstance(job_result, dict) and job_result.get("status") == "failed" else None
            )
            
        except Exception as parse_error:
            logger.warning(f"Failed to parse job result for {job_id}: {parse_error}")
            return JobStatusResponse(
                job_id=job_id,
                status="unknown",
                result=None,
                error=f"Failed to parse job result: {str(parse_error)}"
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
        
        # Get job result directly from Redis (same logic as job status)
        try:
            # Check if the job result exists in Redis
            result_key = f"arq:result:{job_id}"
            raw_result = await redis_pool.get(result_key)
            
            if raw_result is None:
                return VideoLinksResponse(
                    success=False,
                    message="Job not found or expired"
                )
            
            # Try to deserialize the result
            import pickle
            result_data = pickle.loads(raw_result)
            
            # Extract job result
            result = result_data.get('r', {})
            
        except Exception as parse_error:
            logger.warning(f"Failed to parse job result for {job_id}: {parse_error}")
            return VideoLinksResponse(
                success=False,
                message=f"Failed to parse job result: {str(parse_error)}"
            )
        
        if not result:
            return VideoLinksResponse(
                success=False,
                message="Job not found"
            )
        
        # Check if job failed
        if result.get("status") == "failed":
            return VideoLinksResponse(
                success=False,
                message=f"Video rendering failed: {result.get('error', 'Unknown error')}"
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
                        timeout=settings.SHOTSTACK_API_TIMEOUT_SECONDS
                    )
                
                if response.status_code == 200:
                    shotstack_data = response.json().get("response", {})
                    
                    # Log the full response for debugging custom destinations
                    logger.info(f"Shotstack response for render {shotstack_render_id}: {shotstack_data}")
                    
                    # Verificar se já existe transferência em andamento ou concluída
                    destination_service = DestinationService()
                    shotstack_url = shotstack_data.get("url")
                    
                    # Get user_id from the job result (already parsed above)
                    user_id = result.get("user_id", "unknown")
                    
                    if shotstack_url:
                        # Primeiro, verificar se o arquivo já existe no GCS
                        gcs_path = destination_service._generate_gcs_path(user_id, job_id)
                        video_url = destination_service.get_gcs_public_url(gcs_path)
                        
                        # Verificar se arquivo existe no GCS
                        import httpx
                        try:
                            async with httpx.AsyncClient(timeout=settings.GCS_HEAD_REQUEST_TIMEOUT_SECONDS) as client:
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
                            
                            transfer_job_id = f"transfer_{job_id}"
                            logger.info(f"Background transfer queued: {transfer_job_id}")
                            
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

@router.post("/batch-render", response_model=BatchRenderResponse)
async def create_batch_render(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: Dict = Depends(get_current_user)
):
    """
    Process multiple render requests in a single batch
    More efficient for n8n workflows with multiple videos
    Accepts both structured format and direct array from n8n
    """
    try:
        user_id = current_user["user_id"]
        token_service = TokenService()
        usage_service = UsageService()
        
        # Parse request body - handle n8n array format
        body = await request.body()
        import json
        data = json.loads(body)
        
        renders_list = []
        batch_name = None
        
        # Handle different input formats
        if isinstance(data, list):
            # N8N sends array directly: [obj1, obj2, obj3, ...]
            renders_list = data
            logger.info(f"Received direct array format with {len(renders_list)} renders")
        elif isinstance(data, dict):
            if 'renders' in data:
                # Standard format: {"renders": [obj1, obj2, ...]}
                renders_list = data['renders']
                batch_name = data.get('batch_name')
            else:
                # Single object format: treat as one render
                renders_list = [data]
        else:
            raise ValueError("Invalid batch format")
        
        # Validate renders
        if not renders_list:
            raise HTTPException(
                status_code=400,
                detail="No renders provided in batch"
            )
        
        # Calculate total tokens needed
        total_tokens = len(renders_list)
        user_tokens = await token_service.get_user_tokens(user_id)
        
        if user_tokens < total_tokens:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. Need {total_tokens}, have {user_tokens}"
            )
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        job_ids = []
        
        # Get Redis pool
        redis_pool = request.app.state.redis_pool
        
        # Process each render in the batch
        for i, render_data in enumerate(renders_list):
            # Validate render data structure
            if not isinstance(render_data, dict) or 'timeline' not in render_data or 'output' not in render_data:
                logger.error(f"Invalid render data at index {i}: {render_data}")
                continue
                
            # Create RenderRequest object from data
            timeline = render_data['timeline']
            output = render_data['output']
            webhook = render_data.get('webhook')
            destinations = render_data.get('destinations')
            job_id = f"{batch_id}_{i:03d}"
            job_ids.append(job_id)
            
            # Configure destinations
            destination_service = DestinationService()
            output_config = output.copy()
            
            if not destinations:
                destinations = destination_service.get_default_destinations(user_id, job_id)
            else:
                has_gcs = any(dest.get("provider") == "googlecloudstorage" for dest in destinations)
                if not has_gcs:
                    gcs_destinations = destination_service.get_default_destinations(user_id, job_id)
                    destinations.extend([dest for dest in gcs_destinations if dest.get("provider") == "googlecloudstorage"])
            
            output_config["destinations"] = destinations
            
            # Prepare job data
            job_data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "batch_index": i,
                "timeline": timeline,
                "output": output_config,
                "webhook": webhook,
                "tokens_consumed": 1,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Enqueue job
            await redis_pool.enqueue_job(
                "render_video_job",
                job_data,
                _job_id=job_id
            )
            
            # Log in Supabase
            await usage_service.log_render_request(
                user_id=user_id,
                job_id=job_id,
                status='queued',
                tokens_consumed=1,
                metadata={"batch_id": batch_id, "batch_index": i}
            )
        
        # Consume tokens for entire batch
        await token_service.consume_tokens(user_id, total_tokens, f"Batch render: {len(job_ids)} videos")
        
        logger.info(f"Batch {batch_id}: {len(job_ids)} jobs queued for user {user_id}")
        
        return BatchRenderResponse(
            success=True,
            message=f"Batch render queued: {len(job_ids)} videos",
            batch_id=batch_id,
            total_jobs=len(job_ids),
            job_ids=job_ids,
            estimated_tokens_total=total_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch render error: {str(e)}"
        )

@router.post("/batch-render-array", response_model=BatchRenderResponse)
async def create_batch_render_array(
    renders_array: List[Dict[str, Any]],
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Process multiple render requests from n8n array format
    Optimized for n8n direct array input: [obj1, obj2, obj3, ...]
    """
    try:
        user_id = current_user["user_id"]
        token_service = TokenService()
        usage_service = UsageService()
        
        # Validate input
        if not renders_array or not isinstance(renders_array, list):
            raise HTTPException(
                status_code=400,
                detail="Invalid array format"
            )
        
        # Calculate total tokens needed
        total_tokens = len(renders_array)
        user_tokens = await token_service.get_user_tokens(user_id)
        
        if user_tokens < total_tokens:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient tokens. Need {total_tokens}, have {user_tokens}"
            )
        
        # Generate batch ID
        batch_id = str(uuid.uuid4())
        job_ids = []
        
        # Get Redis pool
        redis_pool = request.app.state.redis_pool
        
        # Process each render
        for i, render_data in enumerate(renders_array):
            # Validate render structure
            if not isinstance(render_data, dict) or 'timeline' not in render_data or 'output' not in render_data:
                logger.warning(f"Skipping invalid render at index {i}")
                continue
                
            job_id = f"{batch_id}_{i:03d}"
            job_ids.append(job_id)
            
            # Configure destinations
            destination_service = DestinationService()
            output_config = render_data['output'].copy()
            
            # ✅ CORRIGIR FORMATO SHOTSTACK: width/height -> size
            # Shotstack requer width/height dentro do objeto "size"
            width = output_config.pop('width', None)
            height = output_config.pop('height', None)
            
            if width and height:
                # Converter string para int se necessário
                if isinstance(width, str):
                    width = int(width)
                if isinstance(height, str):
                    height = int(height)
                    
                output_config['size'] = {
                    'width': width,
                    'height': height
                }
                logger.info(f"Converted width/height to size object: {width}x{height}")
            
            # Remover outros campos inválidos
            invalid_fields = ['quality']  # quality deve estar em renditions, não output
            for field in invalid_fields:
                if field in output_config:
                    logger.info(f"Removing invalid Shotstack field '{field}' from output")
                    output_config.pop(field, None)
            
            destinations = destination_service.get_default_destinations(user_id, job_id)
            output_config["destinations"] = destinations
            
            # Prepare job data
            job_data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "batch_index": i,
                "timeline": render_data['timeline'],
                "output": output_config,
                "webhook": render_data.get('webhook'),
                "tokens_consumed": 1,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Enqueue job
            await redis_pool.enqueue_job(
                "render_video_job",
                job_data,
                _job_id=job_id
            )
            
            # Log in Supabase
            await usage_service.log_render_request(
                user_id=user_id,
                job_id=job_id,
                status='queued',
                tokens_consumed=1,
                metadata={"batch_id": batch_id, "batch_index": i, "n8n_array": True}
            )
        
        # Consume tokens for entire batch
        actual_jobs = len(job_ids)
        await token_service.consume_tokens(user_id, actual_jobs, f"N8N Batch: {actual_jobs} videos")
        
        logger.info(f"N8N Batch {batch_id}: {actual_jobs} jobs queued for user {user_id}")
        
        return BatchRenderResponse(
            success=True,
            message=f"N8N Batch processed: {actual_jobs} videos queued",
            batch_id=batch_id,
            total_jobs=actual_jobs,
            job_ids=job_ids,
            estimated_tokens_total=actual_jobs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"N8N Batch render error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"N8N Batch render error: {str(e)}"
        )

@router.get("/batch/{batch_id}/status")
async def get_batch_status(
    batch_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get status of all jobs in a batch
    """
    try:
        redis_pool = request.app.state.redis_pool
        
        # Find all jobs with this batch_id prefix
        batch_jobs = []
        for i in range(100):  # Max 100 jobs per batch
            job_id = f"{batch_id}_{i:03d}"
            
            try:
                result_key = f"arq:result:{job_id}"
                raw_result = await redis_pool.get(result_key)
                
                if raw_result is None:
                    continue
                
                import pickle
                result_data = pickle.loads(raw_result)
                job_result = result_data.get('r', {})
                
                if isinstance(job_result, dict):
                    status = job_result.get('status', 'unknown')
                    batch_jobs.append({
                        "job_id": job_id,
                        "status": status,
                        "shotstack_render_id": job_result.get('shotstack_render_id'),
                        "error": job_result.get('error') if status == 'failed' else None
                    })
                
            except Exception:
                continue
        
        # Calculate batch status
        total_jobs = len(batch_jobs)
        completed_jobs = len([j for j in batch_jobs if j['status'] == 'success'])
        failed_jobs = len([j for j in batch_jobs if j['status'] == 'failed'])
        
        batch_status = "completed" if completed_jobs == total_jobs else "in_progress"
        if failed_jobs > 0:
            batch_status = "partial_failure"
        
        return {
            "batch_id": batch_id,
            "batch_status": batch_status,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "jobs": batch_jobs
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch status error: {str(e)}"
        )

@router.get("/batch/{batch_id}/videos")
async def get_batch_videos(
    batch_id: str,
    request: Request,
    current_user: Dict = Depends(get_current_user)
):
    """
    Get video links for all jobs in a batch (optimized for N8N)
    Returns GCS URLs immediately without external API calls for speed
    """
    try:
        redis_pool = request.app.state.redis_pool
        batch_videos = []
        
        # Find all jobs with this batch_id prefix (optimized - no external calls)
        for i in range(100):  # Max 100 jobs per batch
            job_id = f"{batch_id}_{i:03d}"
            
            try:
                result_key = f"arq:result:{job_id}"
                raw_result = await redis_pool.get(result_key)
                
                if raw_result is None:
                    continue
                
                import pickle
                result_data = pickle.loads(raw_result)
                job_result = result_data.get('r', {})
                
                if not job_result or job_result.get('status') != 'success':
                    continue
                
                shotstack_render_id = job_result.get("shotstack_render_id")
                if not shotstack_render_id:
                    continue
                
                # Generate GCS URL directly without external calls (FAST)
                from ..services.destination_service import DestinationService
                destination_service = DestinationService()
                user_id = job_result.get("user_id", "unknown")
                gcs_path = destination_service._generate_gcs_path(user_id, job_id)
                video_url = destination_service.get_gcs_public_url(gcs_path)
                
                # Queue background transfer without waiting (ASYNC)
                transfer_data = {
                    "shotstack_render_id": shotstack_render_id,
                    "user_id": user_id,
                    "original_job_id": job_id
                }
                
                # Start background job to handle Shotstack API call and transfer
                await redis_pool.enqueue_job(
                    "ensure_video_transferred_job",
                    transfer_data,
                    _job_id=f"ensure_{job_id}"
                )
                
                batch_videos.append({
                    "job_id": job_id,
                    "batch_index": i,
                    "video_url": video_url,
                    "render_id": shotstack_render_id,
                    "transfer_status": "auto_transfer"  # Indica transferência automática em andamento
                })
                
            except Exception as job_error:
                logger.warning(f"Failed to process job {job_id}: {job_error}")
                continue
        
        return {
            "success": True,
            "batch_id": batch_id,
            "total_videos": len(batch_videos),
            "videos": batch_videos
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch videos error: {str(e)}"
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
    Background task to log usage - DEPRECATED: Use direct usage_service calls instead
    """
    try:
        usage_service = UsageService()
        await usage_service.log_render_request(
            user_id=user_id,
            status=action,
            tokens_consumed=tokens_consumed,
            metadata=response_data
        )
    except Exception as e:
        logger.error(f"Error logging usage: {str(e)}")