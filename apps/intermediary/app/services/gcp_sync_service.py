"""
GCP Video Sync Fallback Service

Este serviço verifica periodicamente se existem vídeos no Google Cloud Storage
que estão missing na database (renders com status=completed mas video_url=null).
Atualiza automaticamente a database com as URLs corretas do GCP.

Features:
- Verificação de hora em hora via cron job
- Recuperação de falhas de sincronização automática
- Logging detalhado para monitoramento
- Configuração via environment variables
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.cloud import storage
from app.config import Settings
from app.services.usage_service import UsageService

logger = logging.getLogger(__name__)

class GCPSyncService:
    """Serviço de sincronização entre GCP e database"""
    
    def __init__(self):
        self.settings = Settings()
        self.usage_service = UsageService()
        self.storage_client = None
        
        # Initialize GCS client if credentials are available
        try:
            self.storage_client = storage.Client()
            self.bucket = self.storage_client.bucket(self.settings.GCS_BUCKET)
            logger.info(f"GCP Sync Service initialized with bucket: {self.settings.GCS_BUCKET}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            self.storage_client = None
    
    async def find_missing_video_urls(self) -> List[Dict]:
        """
        Busca renders completed que não têm video_url na database
        
        Returns:
            Lista de renders que precisam de sincronização
        """
        try:
            from supabase import create_client
            supabase = create_client(
                self.settings.SUPABASE_URL,
                self.settings.SUPABASE_SERVICE_ROLE_KEY
            )
            
            # Buscar renders completed sem video_url nos últimos N dias (configurável)
            retention_days = self.settings.GCP_SYNC_RETENTION_DAYS
            cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
            
            response = supabase.table('renders').select(
                'id, job_id, user_id, created_at, updated_at'
            ).eq('status', 'completed').is_('video_url', 'null').gte(
                'created_at', cutoff_date
            ).execute()
            
            missing_videos = response.data or []
            logger.info(f"Found {len(missing_videos)} renders with missing video_url")
            
            return missing_videos
            
        except Exception as e:
            logger.error(f"Error finding missing video URLs: {e}")
            return []
    
    def check_video_exists_in_gcs(self, job_id: str, user_id: str) -> Optional[str]:
        """
        Verifica se o vídeo existe no GCS e retorna a URL pública
        
        Args:
            job_id: ID do job de renderização
            user_id: ID do usuário
            
        Returns:
            URL pública do GCS ou None se não encontrado
        """
        if not self.storage_client:
            logger.error("GCS client not initialized")
            return None
            
        try:
            # Formato do path: videos/2025/08/user_{user_id}/video_{job_id}.mp4
            current_year = datetime.now().year
            current_month = datetime.now().strftime('%m')
            
            # Tentar diferentes variações de nome de arquivo
            possible_paths = [
                f"videos/{current_year}/{current_month}/user_{user_id}/video_{job_id}.mp4",
                f"videos/{current_year}/{current_month}/user_{user_id}/video_{job_id}_000.mp4",
                f"videos/{current_year}/{current_month}/user_{user_id}/{job_id}.mp4",
            ]
            
            for video_path in possible_paths:
                try:
                    blob = self.bucket.blob(video_path)
                    if blob.exists():
                        # Retornar URL pública
                        public_url = f"https://storage.googleapis.com/{self.settings.GCS_BUCKET}/{video_path}"
                        logger.info(f"Found video in GCS: {public_url}")
                        return public_url
                        
                except Exception as path_error:
                    logger.debug(f"Path {video_path} not found: {path_error}")
                    continue
            
            logger.debug(f"Video not found in GCS for job_id: {job_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error checking GCS for job_id {job_id}: {e}")
            return None
    
    async def update_video_url_in_database(self, job_id: str, video_url: str) -> bool:
        """
        Atualiza a video_url na database para um job específico
        
        Args:
            job_id: ID do job
            video_url: URL do vídeo no GCS
            
        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            success = await self.usage_service.update_render_request(
                job_id=job_id,
                video_url=video_url
            )
            
            if success:
                logger.info(f"Updated video_url for job {job_id}: {video_url}")
                return True
            else:
                logger.error(f"Failed to update video_url for job {job_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating video_url for job {job_id}: {e}")
            return False
    
    async def sync_missing_videos(self) -> Dict[str, int]:
        """
        Executa o processo completo de sincronização
        
        Returns:
            Estatísticas do processo de sincronização
        """
        start_time = datetime.now()
        logger.info("🔄 Starting GCP video sync fallback process")
        
        stats = {
            'total_checked': 0,
            'found_in_gcs': 0,
            'successfully_updated': 0,
            'errors': 0
        }
        
        try:
            # 1. Buscar renders com video_url missing
            missing_videos = await self.find_missing_video_urls()
            stats['total_checked'] = len(missing_videos)
            
            if not missing_videos:
                logger.info("✅ No videos with missing URLs found")
                return stats
            
            # 2. Para cada render, verificar se existe no GCS
            for render in missing_videos:
                job_id = render['job_id']
                user_id = render['user_id']
                
                try:
                    # Verificar se o vídeo existe no GCS
                    gcs_url = self.check_video_exists_in_gcs(job_id, user_id)
                    
                    if gcs_url:
                        stats['found_in_gcs'] += 1
                        
                        # Atualizar database com a URL encontrada
                        success = await self.update_video_url_in_database(job_id, gcs_url)
                        
                        if success:
                            stats['successfully_updated'] += 1
                            logger.info(f"✅ Synced video for job {job_id}")
                        else:
                            stats['errors'] += 1
                    else:
                        logger.debug(f"Video not found in GCS for job {job_id}")
                        
                except Exception as render_error:
                    logger.error(f"Error processing render {job_id}: {render_error}")
                    stats['errors'] += 1
            
            # 3. Log final statistics
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"🎯 GCP Sync completed in {duration:.1f}s - "
                f"Checked: {stats['total_checked']}, "
                f"Found: {stats['found_in_gcs']}, "
                f"Updated: {stats['successfully_updated']}, "
                f"Errors: {stats['errors']}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in sync_missing_videos: {e}")
            stats['errors'] += 1
            return stats
    
    async def get_sync_status(self) -> Dict:
        """
        Retorna status detalhado do serviço de sincronização
        
        Returns:
            Status e configurações do serviço
        """
        try:
            missing_videos = await self.find_missing_video_urls()
            
            return {
                'service_status': 'healthy' if self.storage_client else 'gcs_client_error',
                'gcs_bucket': self.settings.GCS_BUCKET,
                'pending_syncs': len(missing_videos),
                'last_check': datetime.now().isoformat(),
                'config': {
                    'retention_days': self.settings.GCP_SYNC_RETENTION_DAYS,
                    'cron_schedule': 'every_hour',
                    'enabled': self.settings.GCP_SYNC_ENABLED
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                'service_status': 'error',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }


# Função global para uso no cron job
async def run_gcp_sync_fallback():
    """
    Função global que executa o processo de sincronização
    Usada pelo cron job no main.py
    """
    sync_service = GCPSyncService()
    stats = await sync_service.sync_missing_videos()
    
    # Log para monitoramento
    logger.info(f"📊 GCP Sync Stats: {stats}")
    
    return stats