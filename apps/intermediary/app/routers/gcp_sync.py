"""
GCP Sync Fallback API Endpoints

Endpoints administrativos para controlar e monitorar o sistema de
sincronização GCP → Database.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from app.services.gcp_sync_service import GCPSyncService, run_gcp_sync_fallback
from app.config import Settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gcp-sync", tags=["GCP Sync"])

settings = Settings()

@router.get("/status", response_model=Dict[str, Any])
async def get_gcp_sync_status():
    """
    Retorna status atual do serviço de sincronização GCP
    
    Returns:
        - service_status: Status do serviço (healthy, error, gcs_client_error)
        - gcs_bucket: Nome do bucket configurado
        - pending_syncs: Número de vídeos pendentes de sincronização
        - last_check: Timestamp da última verificação
        - config: Configurações do serviço
    """
    try:
        sync_service = GCPSyncService()
        status = await sync_service.get_sync_status()
        
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Error getting GCP sync status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting sync status: {str(e)}"
        )

@router.post("/run", response_model=Dict[str, Any])
async def run_manual_gcp_sync():
    """
    Executa manualmente o processo de sincronização GCP
    
    Útil para:
    - Testar o sistema de sincronização
    - Forçar sincronização após falhas conhecidas
    - Verificação manual sem aguardar o cron job
    
    Returns:
        Estatísticas do processo de sincronização
    """
    try:
        logger.info("🔧 Manual GCP sync requested")
        
        stats = await run_gcp_sync_fallback()
        
        return {
            "success": True,
            "message": "GCP sync completed successfully",
            "data": {
                "statistics": stats,
                "summary": f"Checked {stats['total_checked']} videos, updated {stats['successfully_updated']} URLs"
            }
        }
        
    except Exception as e:
        logger.error(f"Error running manual GCP sync: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running sync: {str(e)}"
        )

@router.get("/missing-videos", response_model=Dict[str, Any])
async def get_missing_videos():
    """
    Lista vídeos que têm status=completed mas video_url=null
    
    Útil para:
    - Identificar quantos vídeos estão aguardando sincronização
    - Debug de problemas de sincronização
    - Monitoramento de falhas de transfer
    
    Returns:
        Lista de renders que precisam de sincronização
    """
    try:
        sync_service = GCPSyncService()
        missing_videos = await sync_service.find_missing_video_urls()
        
        return {
            "success": True,
            "data": {
                "count": len(missing_videos),
                "videos": missing_videos
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting missing videos: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting missing videos: {str(e)}"
        )

@router.post("/test-gcs-connection", response_model=Dict[str, Any])
async def test_gcs_connection():
    """
    Testa a conexão com o Google Cloud Storage
    
    Útil para:
    - Verificar se as credenciais GCS estão corretas
    - Testar se o bucket está acessível
    - Debug de problemas de conectividade
    
    Returns:
        Status da conexão GCS
    """
    try:
        sync_service = GCPSyncService()
        
        if not sync_service.storage_client:
            return {
                "success": False,
                "error": "GCS client not initialized. Check GOOGLE_APPLICATION_CREDENTIALS."
            }
        
        # Testar acesso ao bucket
        bucket_exists = sync_service.bucket.exists()
        
        if bucket_exists:
            # Listar alguns objetos como teste
            blobs = list(sync_service.storage_client.list_blobs(
                sync_service.settings.GCS_BUCKET, 
                prefix="videos/", 
                max_results=5
            ))
            
            return {
                "success": True,
                "data": {
                    "bucket_name": sync_service.settings.GCS_BUCKET,
                    "bucket_exists": True,
                    "sample_objects_count": len(blobs),
                    "connection_status": "healthy"
                }
            }
        else:
            return {
                "success": False,
                "error": f"Bucket {sync_service.settings.GCS_BUCKET} does not exist or is not accessible"
            }
            
    except Exception as e:
        logger.error(f"Error testing GCS connection: {e}")
        return {
            "success": False,
            "error": f"GCS connection failed: {str(e)}"
        }

@router.get("/config", response_model=Dict[str, Any])
async def get_gcp_sync_config():
    """
    Retorna configurações atuais do serviço de sincronização
    
    Returns:
        Configurações do serviço
    """
    try:
        return {
            "success": True,
            "data": {
                "gcs_bucket": settings.GCS_BUCKET,
                "supabase_url": settings.SUPABASE_URL,
                "sync_schedule": "every_hour",
                "retention_days": 7,
                "environment": "development" if "localhost" in settings.SUPABASE_URL else "production"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting config: {str(e)}"
        )