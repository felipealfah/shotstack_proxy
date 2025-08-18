from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
from pydantic import BaseModel, Field
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
from ..middleware.auth import get_current_user, verify_api_key_with_email

logger = logging.getLogger(__name__)
router = APIRouter()


class RenderRequest(BaseModel):
    timeline: Dict[str, Any] = Field(
        ...,
        description="🎬 Estrutura completa do vídeo com tracks, clips e assets",
        example={
            "background": "#000000",
            "tracks": [{
                "clips": [{
                    "asset": {
                        "type": "title",
                        "text": "Meu Primeiro Vídeo",
                        "style": "minimal"
                    },
                    "start": 0,
                    "length": 5
                }]
            }]
        }
    )
    output: Dict[str, Any] = Field(
        ...,
        description="📊 Configurações de saída do vídeo (formato, resolução, qualidade)",
        example={
            "format": "mp4",
            "resolution": "hd",
            "fps": 25,
            "quality": "medium"
        }
    )
    destinations: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="☁️ Destinos customizados (opcional - GCS é automático)",
        example=[
            {
                "provider": "s3",
                "options": {
                    "region": "us-east-1",
                    "bucket": "my-bucket",
                    "path": "videos/"
                }
            }
        ]
    )
    webhook: Optional[str] = Field(
        None,
        description="🔔 URL para notificação quando vídeo estiver pronto",
        example="https://myapp.com/webhook/video-complete"
    )

class RenderResponse(BaseModel):
    success: bool = Field(..., description="✅ Indica se o job foi aceito com sucesso")
    message: str = Field(..., description="📝 Mensagem descritiva do resultado", example="Render job queued successfully")
    job_id: str = Field(..., description="🆔 ID único do job para monitoramento", example="cf6a6061-9204-4d9b-b363-3a896d11661e")
    estimated_tokens: float = Field(1.0, description="💰 Tokens consumidos para este render (proporcional)", example=0.5)
    
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class VideoLinksResponse(BaseModel):
    success: bool = Field(..., description="✅ Indica se o vídeo está disponível")
    message: str = Field(..., description="📝 Status ou mensagem de erro", example="Video ready for download")
    video_url: Optional[str] = Field(
        None, 
        description="🔗 URL direta do Google Cloud Storage para download",
        example="https://storage.googleapis.com/ffmpeg-api/videos/2025/08/user_123/video_abc123.mp4"
    )
    poster_url: Optional[str] = Field(
        None, 
        description="🖼️ URL da imagem de capa (poster) do vídeo",
        example="https://storage.googleapis.com/ffmpeg-api/posters/poster_abc123.jpg"
    )
    thumbnail_url: Optional[str] = Field(
        None, 
        description="🖼️ URL da miniatura do vídeo",
        example="https://storage.googleapis.com/ffmpeg-api/thumbnails/thumb_abc123.jpg"
    )
    render_id: Optional[str] = Field(
        None, 
        description="🎬 ID do render interno",
        example="f5fe3507-0bf7-44e7-83b2-abd5adf503d2"
    )
    transfer_status: Optional[str] = Field(
        None, 
        description="📊 Status da transferência para GCS",
        example="completed",
        enum=["completed", "in_progress", "pending", "failed"]
    )

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
    success: bool = Field(..., description="✅ Indica se o batch foi aceito com sucesso")
    message: str = Field(..., description="📝 Mensagem descritiva do resultado", example="Batch render queued successfully")
    batch_id: str = Field(..., description="🆔 ID único do batch para monitoramento", example="batch_abc123def456")
    total_jobs: int = Field(..., description="📊 Número total de vídeos no batch", example=5)
    job_ids: List[str] = Field(
        ..., 
        description="🎬 Lista de IDs individuais para cada vídeo",
        example=["abc123_000", "abc123_001", "abc123_002"]
    )
    estimated_tokens_total: float = Field(..., description="💰 Total de tokens consumidos (proporcional)", example=2.5)


@router.post("/render", response_model=RenderResponse)
async def create_render(
    render_request: RenderRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: Dict = Depends(verify_api_key_with_email)
):
    """
    ## 🎬 Renderização Individual de Vídeo
    
    Cria um único vídeo através da plataforma Aion Videos com transferência automática para Google Cloud Storage.
    
    ### 📋 Como Funciona:
    1. **Token Validation**: Verifica se você tem tokens suficientes (1 token por vídeo)
    2. **Job Queue**: Enfileira o job para processamento em background
    3. **Video Processing**: Renderiza o vídeo usando nossa engine de alta qualidade
    4. **Auto Transfer**: Transfere automaticamente para Google Cloud Storage
    5. **Notification**: Vídeo fica disponível para download via `/videos/{job_id}`
    
    ### ⏱️ Tempo de Processamento:
    - **Vídeos simples** (texto, imagens): 30-60 segundos
    - **Vídeos complexos** (efeitos, transições): 1-3 minutos
    - **Vídeos longos** (>30s): 2-5 minutos
    
    ### 💰 Custo:
    - **1 token** por vídeo renderizado
    - Tokens são consumidos imediatamente ao enfileirar o job
    - Reembolso automático em caso de falha
    
    ### 🔐 Autenticação Obrigatória:
    **Headers necessários:**
    ```
    Authorization: Bearer YOUR_API_KEY
    X-User-Email: your@email.com
    ```
    
    ### 📊 Status Codes:
    - **202**: Job aceito e enfileirado com sucesso
    - **402**: Tokens insuficientes
    - **400**: Payload inválido
    - **401**: API Key inválida ou email não corresponde
    - **422**: Header X-User-Email ausente
    
    ### 🎯 Exemplo de Timeline:
    ```json
    {
      "timeline": {
        "background": "#000000",
        "tracks": [{
          "clips": [{
            "asset": {
              "type": "title",
              "text": "Meu Primeiro Vídeo",
              "style": "minimal"
            },
            "start": 0,
            "length": 5
          }]
        }]
      },
      "output": {
        "format": "mp4",
        "resolution": "hd"
      }
    }
    ```
    
    ### 🔄 Próximos Passos:
    1. Use `/job/{job_id}` para monitorar o status
    2. Quando status = "completed", acesse `/videos/{job_id}` 
    3. Download direto via URL do Google Cloud Storage
    """
    try:
        user_id = current_user["user_id"]
        
        # Check if user has enough tokens
        token_service = TokenService()
        user_tokens = await token_service.get_user_tokens(user_id)
        
        # Calculate tokens needed based on video duration (proportional)
        from ..services.timeline_parser import TimelineParser
        
        duration_seconds = TimelineParser.extract_total_duration(render_request.timeline)
        tokens_needed = await token_service.calculate_tokens_for_duration(duration_seconds)
        
        logger.info(f"Video duration: {duration_seconds}s, tokens needed: {tokens_needed}")
        
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
    current_user: Dict = Depends(verify_api_key_with_email)
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
    current_user: Dict = Depends(verify_api_key_with_email)
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
    current_user: Dict = Depends(verify_api_key_with_email)
):
    """
    ## 🎬 Acesso e Download de Vídeos
    
    **Obtenha links de download** para vídeos renderizados pela plataforma Aion Videos e transferidos para Google Cloud Storage.
    
    ### 📋 Como Funciona:
    1. **Job Validation**: Verifica se o job_id existe e foi processado
    2. **Status Check**: Confirma que a renderização foi concluída
    3. **GCS URLs**: Retorna URLs diretas do Google Cloud Storage
    4. **Expiration Info**: Informa quando o vídeo expira (48h)
    
    ### 🔐 Autenticação Obrigatória:
    **Headers necessários:**
    ```
    Authorization: Bearer YOUR_API_KEY
    X-User-Email: your@email.com
    ```
    
    ### ⏱️ Disponibilidade:
    - **Imediata**: Assim que status = "completed"
    - **Duração**: 48 horas (2 dias) após renderização
    - **Auto-Delete**: GCS remove automaticamente após expiração
    
    ### 📊 Response de Sucesso:
    ```json
    {
      "success": true,
      "job_id": "abc123-def456-ghi789",
      "video_url": "https://storage.googleapis.com/ffmpeg-api/videos/2025/08/user_123/video_abc123.mp4",
      "shotstack_url": "https://cdn.shotstack.io/au/prod/...",
      "status": "ready",
      "file_size": 16850432,
      "duration": 5.0,
      "expires_at": "2025-08-17T10:30:00Z"
    }
    ```
    
    ### 🔗 URLs Disponíveis:
    - **video_url**: Google Cloud Storage (recomendado) - Mais rápido e confiável
    - **shotstack_url**: CDN Backup - URL alternativa para redundância
    
    ### ⚠️ Status Possíveis:
    - **ready**: Vídeo disponível para download
    - **expired**: Vídeo expirado (>48h)
    - **processing**: Ainda renderizando
    - **failed**: Falha na renderização
    
    ### 🚫 Erros Comuns:
    - **404**: Job ID não encontrado ou expirado
    - **425**: Vídeo ainda processando (tente novamente em 30s)
    - **410**: Vídeo expirado (>48h desde criação)
    
    ### 💡 Dicas de Uso:
    - **Download Direto**: Use video_url para download/streaming
    - **Integração**: Ideal para N8N, webhooks e automações
    - **Batch Access**: Para múltiplos vídeos, use `/batch/{batch_id}/videos`
    
    ### 🔄 Workflow Recomendado:
    1. Renderize vídeo via `/render` ou `/batch-render-array`
    2. Monitore status via `/job/{job_id}`
    3. Quando completed, acesse este endpoint
    4. Faça download/use a URL dentro de 48h
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
                        potential_video_url = destination_service.get_gcs_public_url(gcs_path)
                        
                        # Verificar se arquivo existe no GCS
                        import httpx
                        video_url = None  # Inicializar como None
                        
                        try:
                            async with httpx.AsyncClient(timeout=settings.GCS_HEAD_REQUEST_TIMEOUT_SECONDS) as client:
                                gcs_check = await client.head(potential_video_url)
                                if gcs_check.status_code == 200:
                                    # ✅ Arquivo existe no GCS, pode retornar URL
                                    video_url = potential_video_url
                                    logger.info(f"Video confirmed in GCS: {video_url}")
                                else:
                                    raise httpx.HTTPStatusError("File not found", request=None, response=gcs_check)
                        except:
                            # Arquivo não existe no GCS, iniciar transferência em background
                            logger.info(f"Video not found in GCS, starting background transfer for render {shotstack_render_id}")
                            
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
                            
                            # ✅ NÃO retornar URL até que upload seja concluído
                            video_url = None
                        
                    else:
                        logger.error(f"No Shotstack URL found in response for render {shotstack_render_id}")
                        video_url = None
                    
                    # URLs de poster e thumbnail (ficam no Shotstack CDN)
                    poster_url = shotstack_data.get("poster")
                    thumbnail_url = shotstack_data.get("thumbnail")
                    
                    # Determinar status da transferência baseado na existência da URL
                    if video_url:
                        transfer_status = "completed"
                        logger.info(f"Transfer status: completed - video available at {video_url}")
                    else:
                        transfer_status = "in_progress"
                        logger.info(f"Transfer status: in_progress - video upload queued for job {job_id}")
                    
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
    current_user: Dict = Depends(verify_api_key_with_email)
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
        
        # Calculate total tokens needed based on video durations (proportional)
        from ..services.timeline_parser import TimelineParser
        
        total_tokens = 0
        duration_details = []
        
        for i, render_data in enumerate(renders_list):
            if not isinstance(render_data, dict) or 'timeline' not in render_data:
                logger.warning(f"Skipping invalid render at index {i} - missing timeline")
                continue
                
            duration_seconds = TimelineParser.extract_total_duration(render_data['timeline'])
            tokens_for_this_video = await token_service.calculate_tokens_for_duration(duration_seconds)
            total_tokens += tokens_for_this_video
            
            duration_details.append({
                "index": i,
                "duration_seconds": duration_seconds,
                "tokens": tokens_for_this_video
            })
        
        logger.info(f"Structured batch token calculation: {len(duration_details)} videos, total {total_tokens} tokens")
        for detail in duration_details:
            logger.info(f"  Video {detail['index']}: {detail['duration_seconds']}s = {detail['tokens']} tokens")
        
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
            
            # Get tokens for this specific video from duration_details
            tokens_for_this_video = 1  # fallback
            for detail in duration_details:
                if detail["index"] == i:
                    tokens_for_this_video = detail["tokens"]
                    break
            
            # Prepare job data
            job_data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "batch_index": i,
                "timeline": timeline,
                "output": output_config,
                "webhook": webhook,
                "tokens_consumed": tokens_for_this_video,
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
                tokens_consumed=tokens_for_this_video,
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
    current_user: Dict = Depends(verify_api_key_with_email)
):
    """
    ## 🤖 Renderização em Lote - Formato N8N Array
    
    **Endpoint otimizado para N8N workflows** - processa múltiplos vídeos simultaneamente através da plataforma Aion Videos.
    
    ### 🎯 Ideal Para:
    - **N8N Workflows**: Integração direta sem reestruturação
    - **Produção em Escala**: 2-50 vídeos por requisição
    - **Automação**: Pipelines de vídeo automatizados
    - **Batch Processing**: Processamento eficiente em lote
    
    ### 📋 Como Funciona:
    1. **Array Input**: Aceita array direto `[obj1, obj2, obj3, ...]`
    2. **Token Calculation**: Calcula tokens total (1 por vídeo)
    3. **Parallel Processing**: Todos os jobs são enfileirados simultaneamente
    4. **Batch Tracking**: Retorna `batch_id` único para monitoramento
    5. **Individual Access**: Cada vídeo acessível via `job_id` individual
    
    ### ⚡ Performance:
    - **Processamento Paralelo**: Até 50 vídeos simultâneos
    - **Tempo Otimizado**: Não há overhead entre vídeos
    - **Worker Pool**: 20-180 workers disponíveis (escalável)
    
    ### 🎯 Formato de Input (Array):
    ```json
    [
      {
        "timeline": {
          "background": "#000000",
          "tracks": [{
            "clips": [{
              "asset": {
                "type": "title",
                "text": "Vídeo 1",
                "style": "minimal"
              },
              "start": 0,
              "length": 3
            }]
          }]
        },
        "output": {
          "format": "mp4",
          "width": "1280",
          "height": "720"
        }
      },
      {
        "timeline": {
          "background": "#0000FF",
          "tracks": [{
            "clips": [{
              "asset": {
                "type": "title", 
                "text": "Vídeo 2",
                "style": "minimal"
              },
              "start": 0,
              "length": 3
            }]
          }]
        },
        "output": {
          "format": "mp4",
          "width": "1920", 
          "height": "1080"
        }
      }
    ]
    ```
    
    ### 📊 Response:
    ```json
    {
      "success": true,
      "batch_id": "batch_abc123def456",
      "job_ids": ["abc123_000", "abc123_001"],
      "total_videos": 2,
      "tokens_consumed": 2
    }
    ```
    
    ### 🔄 Monitoramento:
    - **Batch Status**: `GET /batch/{batch_id}/status`
    - **All Videos**: `GET /batch/{batch_id}/videos` 
    - **Individual**: `GET /videos/{job_id}`
    
    ### 💰 Custo:
    - **1 token por vídeo** no array
    - **Máximo 50 vídeos** por requisição
    - **Reembolso automático** para falhas individuais
    
    ### 🎉 N8N Integration:
    1. **HTTP Request Node**: POST para este endpoint
    2. **Body**: Array direto dos vídeos
    3. **Wait Node**: 60-180 segundos
    4. **Status Check**: Verificar batch status
    5. **Download**: Acessar vídeos via URLs GCS
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
        
        # Calculate total tokens needed based on video durations (proportional)
        from ..services.timeline_parser import TimelineParser
        
        total_tokens = 0
        duration_details = []
        
        for i, render_data in enumerate(renders_array):
            if not isinstance(render_data, dict) or 'timeline' not in render_data:
                logger.warning(f"Skipping invalid render at index {i} - missing timeline")
                continue
                
            duration_seconds = TimelineParser.extract_total_duration(render_data['timeline'])
            tokens_for_this_video = await token_service.calculate_tokens_for_duration(duration_seconds)
            total_tokens += tokens_for_this_video
            
            duration_details.append({
                "index": i,
                "duration_seconds": duration_seconds,
                "tokens": tokens_for_this_video
            })
        
        logger.info(f"Batch token calculation: {len(duration_details)} videos, total {total_tokens} tokens")
        for detail in duration_details:
            logger.info(f"  Video {detail['index']}: {detail['duration_seconds']}s = {detail['tokens']} tokens")
        
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
            
            # Get tokens for this specific video from duration_details
            tokens_for_this_video = 1  # fallback
            for detail in duration_details:
                if detail["index"] == i:
                    tokens_for_this_video = detail["tokens"]
                    break
            
            # Prepare job data
            job_data = {
                "user_id": user_id,
                "batch_id": batch_id,
                "batch_index": i,
                "timeline": render_data['timeline'],
                "output": output_config,
                "webhook": render_data.get('webhook'),
                "tokens_consumed": tokens_for_this_video,
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
                tokens_consumed=tokens_for_this_video,
                metadata={"batch_id": batch_id, "batch_index": i, "n8n_array": True}
            )
        
        # Consume tokens for entire batch (proportional total)
        actual_jobs = len(job_ids)
        await token_service.consume_tokens(user_id, total_tokens, f"N8N Batch: {actual_jobs} videos, {total_tokens} tokens")
        
        logger.info(f"N8N Batch {batch_id}: {actual_jobs} jobs queued for user {user_id}")
        
        return BatchRenderResponse(
            success=True,
            message=f"N8N Batch processed: {actual_jobs} videos queued, {total_tokens} tokens consumed",
            batch_id=batch_id,
            total_jobs=actual_jobs,
            job_ids=job_ids,
            estimated_tokens_total=total_tokens
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
    current_user: Dict = Depends(verify_api_key_with_email)
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
    current_user: Dict = Depends(verify_api_key_with_email)
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
                
                # Generate GCS path for potential URL (FAST - no external calls)
                from ..services.destination_service import DestinationService
                destination_service = DestinationService()
                user_id = job_result.get("user_id", "unknown")
                gcs_path = destination_service._generate_gcs_path(user_id, job_id)
                
                # ✅ Para batch endpoints otimizados: retornar URL potencial com status
                # O frontend pode polling para verificar quando estiver disponível
                potential_video_url = destination_service.get_gcs_public_url(gcs_path)
                
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
                    "video_url": potential_video_url,  # URL potencial - pode não estar disponível ainda
                    "render_id": shotstack_render_id,
                    "transfer_status": "pending",  # Mais preciso que "auto_transfer"
                    "note": "URL may not be available immediately - check transfer_status"
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


@router.get("/video-status/{job_id}")
async def check_video_upload_status(
    job_id: str,
    request: Request,
    current_user: Dict = Depends(verify_api_key_with_email)
):
    """
    Verifica se um vídeo foi transferido para GCS e está disponível
    
    Args:
        job_id: ID do job de renderização
        
    Returns:
        Status do upload e URL se disponível
    """
    try:
        user_id = current_user.get("id", "unknown")
        
        # Generate potential GCS URL
        from ..services.destination_service import DestinationService
        destination_service = DestinationService()
        gcs_path = destination_service._generate_gcs_path(user_id, job_id)
        potential_video_url = destination_service.get_gcs_public_url(gcs_path)
        
        # Check if file exists in GCS
        import httpx
        try:
            async with httpx.AsyncClient(timeout=settings.GCS_HEAD_REQUEST_TIMEOUT_SECONDS) as client:
                gcs_check = await client.head(potential_video_url)
                if gcs_check.status_code == 200:
                    return {
                        "success": True,
                        "status": "completed",
                        "video_url": potential_video_url,
                        "message": "Video is available in GCS"
                    }
                else:
                    return {
                        "success": True,
                        "status": "in_progress", 
                        "video_url": None,
                        "message": "Video upload still in progress"
                    }
        except Exception as e:
            return {
                "success": True,
                "status": "in_progress",
                "video_url": None, 
                "message": f"Video upload still in progress: {str(e)}"
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking video status: {str(e)}"
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