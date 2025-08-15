"""
Serviço para transferência de vídeos em background
"""
import asyncio
import logging
import os
from typing import Dict, Any
from .destination_service import DestinationService
from ..config import settings

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

async def ensure_video_transferred_job(ctx, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job otimizado para garantir que vídeo seja transferido para GCS
    Faz chamadas ao Shotstack API em background para não bloquear N8N
    
    Args:
        ctx: ARQ context
        transfer_data: Dados com shotstack_render_id, user_id, original_job_id
        
    Returns:
        Resultado da verificação/transferência
    """
    job_id = ctx.get('job_id', 'unknown')
    logger.info(f"Starting ensure video transfer job {job_id}")
    
    try:
        shotstack_render_id = transfer_data.get('shotstack_render_id')
        user_id = transfer_data.get('user_id', 'unknown')
        original_job_id = transfer_data.get('original_job_id')
        
        if not shotstack_render_id or not original_job_id:
            raise ValueError("Missing required transfer data")
        
        # Verificar status no Shotstack API
        import httpx
        
        shotstack_api_url = os.getenv('SHOTSTACK_API_URL', 'https://api.shotstack.io/v1')
        shotstack_api_key = os.getenv('SHOTSTACK_API_KEY')
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{shotstack_api_url}/render/{shotstack_render_id}",
                headers={
                    "x-api-key": shotstack_api_key,
                    "Content-Type": "application/json"
                },
                timeout=settings.SHOTSTACK_API_TIMEOUT_SECONDS
            )
        
        if response.status_code != 200:
            logger.warning(f"Shotstack API error for render {shotstack_render_id}: {response.status_code}")
            return {
                "status": "pending",
                "job_id": job_id,
                "original_job_id": original_job_id,
                "message": "Shotstack render not ready yet"
            }
        
        shotstack_data = response.json().get("response", {})
        render_status = shotstack_data.get("status")
        
        if render_status != "done":
            logger.info(f"Render {shotstack_render_id} status: {render_status}")
            return {
                "status": "pending",
                "job_id": job_id,
                "original_job_id": original_job_id,
                "render_status": render_status,
                "message": f"Render status: {render_status}"
            }
        
        # Render concluído, verificar se arquivo existe no GCS
        destination_service = DestinationService()
        gcs_path = destination_service._generate_gcs_path(user_id, original_job_id)
        gcs_url = destination_service.get_gcs_public_url(gcs_path)
        
        # Verificar se arquivo já existe no GCS
        try:
            async with httpx.AsyncClient(timeout=3.0) as check_client:
                gcs_check = await check_client.head(gcs_url)
                if gcs_check.status_code == 200:
                    logger.info(f"Video already exists in GCS: {gcs_url}")
                    return {
                        "status": "completed",
                        "job_id": job_id,
                        "original_job_id": original_job_id,
                        "gcs_url": gcs_url,
                        "message": "Video already in GCS"
                    }
        except:
            pass  # Arquivo não existe, continuar com transferência
        
        # Iniciar transferência para GCS
        shotstack_url = shotstack_data.get("url")
        if not shotstack_url:
            raise ValueError("No Shotstack URL found in render response")
        
        logger.info(f"Starting GCS transfer for job {original_job_id}")
        gcs_url = await destination_service.transfer_to_gcs(
            shotstack_url, user_id, original_job_id
        )
        
        logger.info(f"Video transferred to GCS: {gcs_url}")
        return {
            "status": "completed",
            "job_id": job_id,
            "original_job_id": original_job_id,
            "gcs_url": gcs_url,
            "shotstack_url": shotstack_url,
            "message": "Transfer completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Ensure video transfer failed: {str(e)}")
        return {
            "status": "failed",
            "job_id": job_id,
            "original_job_id": transfer_data.get('original_job_id'),
            "error": str(e),
            "message": f"Transfer failed: {str(e)}"
        }

async def auto_transfer_when_ready_job(ctx, transfer_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Job automático para transferir vídeo quando Shotstack render estiver pronto
    Verifica status periodicamente e transfere automaticamente quando "done"
    
    Args:
        ctx: ARQ context
        transfer_data: Dados com shotstack_render_id, user_id, original_job_id
        
    Returns:
        Resultado da verificação/transferência ou reagendamento
    """
    job_id = ctx.get('job_id', 'unknown')
    logger.info(f"Starting auto-transfer monitoring job {job_id}")
    
    try:
        shotstack_render_id = transfer_data.get('shotstack_render_id')
        user_id = transfer_data.get('user_id', 'unknown')
        original_job_id = transfer_data.get('original_job_id')
        attempt = transfer_data.get('attempt', 1)
        max_attempts = 20  # Max 20 tentativas = ~10 minutos
        
        if not shotstack_render_id or not original_job_id:
            raise ValueError("Missing required transfer data")
        
        logger.info(f"Checking Shotstack render {shotstack_render_id} (attempt {attempt})")
        
        # Verificar status no Shotstack API
        import httpx
        
        shotstack_api_url = os.getenv('SHOTSTACK_API_URL', 'https://api.shotstack.io/v1')
        shotstack_api_key = os.getenv('SHOTSTACK_API_KEY')
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{shotstack_api_url}/render/{shotstack_render_id}",
                headers={
                    "x-api-key": shotstack_api_key,
                    "Content-Type": "application/json"
                },
                timeout=settings.SHOTSTACK_API_TIMEOUT_SECONDS
            )
        
        if response.status_code != 200:
            if attempt >= max_attempts:
                logger.error(f"Max attempts reached for render {shotstack_render_id}")
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "original_job_id": original_job_id,
                    "message": f"Max attempts reached, Shotstack API error: {response.status_code}"
                }
            
            # Reagendar para tentar novamente em 30s
            logger.warning(f"Shotstack API error {response.status_code}, rescheduling...")
            return await reschedule_auto_transfer(ctx, transfer_data, attempt + 1)
        
        shotstack_data = response.json().get("response", {})
        render_status = shotstack_data.get("status")
        
        logger.info(f"Render {shotstack_render_id} status: {render_status}")
        
        if render_status == "done":
            # ✅ RENDER CONCLUÍDO - INICIAR TRANSFERÊNCIA AUTOMÁTICA
            shotstack_url = shotstack_data.get("url")
            if not shotstack_url:
                raise ValueError("No Shotstack URL found in completed render")
            
            logger.info(f"🎉 Render {shotstack_render_id} DONE! Starting automatic transfer...")
            
            # Verificar se arquivo já existe no GCS
            destination_service = DestinationService()
            gcs_path = destination_service._generate_gcs_path(user_id, original_job_id)
            gcs_url = destination_service.get_gcs_public_url(gcs_path)
            
            try:
                async with httpx.AsyncClient(timeout=3.0) as check_client:
                    gcs_check = await check_client.head(gcs_url)
                    if gcs_check.status_code == 200:
                        logger.info(f"Video already exists in GCS: {gcs_url}")
                        
                        # ✅ SINCRONIZAR VIDEO URL COM SUPABASE (video já existe)
                        try:
                            from app.services.usage_service import UsageService
                            usage_service = UsageService()
                            await usage_service.update_render_request(
                                job_id=original_job_id,
                                video_url=gcs_url
                            )
                            logger.info(f"Updated Supabase video_url for existing job {original_job_id}: {gcs_url}")
                        except Exception as sync_error:
                            logger.error(f"Failed to sync video_url to Supabase for existing job {original_job_id}: {sync_error}")
                        
                        return {
                            "status": "completed",
                            "job_id": job_id,
                            "original_job_id": original_job_id,
                            "gcs_url": gcs_url,
                            "message": "Video already in GCS"
                        }
            except:
                pass  # Arquivo não existe, continuar com transferência
            
            # Executar transferência automática
            logger.info(f"Transferring video automatically for job {original_job_id}")
            gcs_url = await destination_service.transfer_to_gcs(
                shotstack_url, user_id, original_job_id
            )
            
            logger.info(f"🎉 AUTO-TRANSFER COMPLETED: {gcs_url}")
            
            # ✅ SINCRONIZAR VIDEO URL COM SUPABASE
            try:
                from app.services.usage_service import UsageService
                usage_service = UsageService()
                await usage_service.update_render_request(
                    job_id=original_job_id,
                    video_url=gcs_url
                )
                logger.info(f"Updated Supabase video_url for job {original_job_id}: {gcs_url}")
            except Exception as sync_error:
                logger.error(f"Failed to sync video_url to Supabase for job {original_job_id}: {sync_error}")
            
            return {
                "status": "completed",
                "job_id": job_id,
                "original_job_id": original_job_id,
                "gcs_url": gcs_url,
                "shotstack_url": shotstack_url,
                "message": "Automatic transfer completed successfully",
                "render_status": render_status
            }
            
        elif render_status in ["queued", "rendering", "processing"]:
            # 🔄 AINDA PROCESSANDO - REAGENDAR
            if attempt >= max_attempts:
                logger.warning(f"Max attempts reached for render {shotstack_render_id}, status: {render_status}")
                return {
                    "status": "timeout",
                    "job_id": job_id,
                    "original_job_id": original_job_id,
                    "render_status": render_status,
                    "message": f"Render timeout after {max_attempts} attempts, last status: {render_status}"
                }
            
            logger.info(f"Render still {render_status}, rescheduling check...")
            return await reschedule_auto_transfer(ctx, transfer_data, attempt + 1)
            
        elif render_status == "failed":
            # ❌ RENDER FALHOU
            logger.error(f"Render {shotstack_render_id} failed")
            return {
                "status": "failed",
                "job_id": job_id,
                "original_job_id": original_job_id,
                "render_status": render_status,
                "message": "Shotstack render failed"
            }
        
        else:
            # ❓ STATUS DESCONHECIDO
            logger.warning(f"Unknown render status: {render_status}")
            if attempt >= max_attempts:
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "original_job_id": original_job_id,
                    "render_status": render_status,
                    "message": f"Unknown status after {max_attempts} attempts: {render_status}"
                }
            
            return await reschedule_auto_transfer(ctx, transfer_data, attempt + 1)
        
    except Exception as e:
        logger.error(f"Auto-transfer monitoring failed: {str(e)}")
        return {
            "status": "failed",
            "job_id": job_id,
            "original_job_id": transfer_data.get('original_job_id'),
            "error": str(e),
            "message": f"Auto-transfer monitoring failed: {str(e)}"
        }

async def reschedule_auto_transfer(ctx, transfer_data: Dict[str, Any], next_attempt: int) -> Dict[str, Any]:
    """
    Reagenda o job de auto-transferência para tentar novamente
    """
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        
        # Atualizar dados para próxima tentativa
        updated_data = transfer_data.copy()
        updated_data['attempt'] = next_attempt
        
        # Calcular delay baseado na tentativa (backoff)
        if next_attempt <= 5:
            delay = 30  # Primeiras 5 tentativas: 30s
        elif next_attempt <= 10:
            delay = 60  # Tentativas 6-10: 60s
        else:
            delay = 120  # Tentativas 11+: 120s
        
        redis_settings = RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
        pool = await create_pool(redis_settings)
        
        original_job_id = transfer_data.get('original_job_id')
        await pool.enqueue_job(
            "auto_transfer_when_ready_job",
            updated_data,
            _job_id=f"auto_transfer_{original_job_id}",
            _defer_by=delay
        )
        
        await pool.close()
        
        logger.info(f"Rescheduled auto-transfer for job {original_job_id} (attempt {next_attempt}) in {delay}s")
        return {
            "status": "rescheduled",
            "job_id": ctx.get('job_id', 'unknown'),
            "original_job_id": original_job_id,
            "next_attempt": next_attempt,
            "delay": delay,
            "message": f"Rescheduled for attempt {next_attempt} in {delay}s"
        }
        
    except Exception as e:
        logger.error(f"Failed to reschedule auto-transfer: {str(e)}")
        return {
            "status": "failed",
            "job_id": ctx.get('job_id', 'unknown'),
            "original_job_id": transfer_data.get('original_job_id'),
            "error": str(e),
            "message": f"Failed to reschedule: {str(e)}"
        }