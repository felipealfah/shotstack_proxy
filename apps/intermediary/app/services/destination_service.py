from typing import Dict, List, Any
from datetime import datetime
import logging
from ..config import settings

logger = logging.getLogger(__name__)

class DestinationService:
    """
    Serviço para gerenciar destinos de armazenamento para renderizações
    """
    
    def __init__(self):
        self.gcs_bucket = settings.GCS_BUCKET
        self.gcs_path_prefix = settings.GCS_PATH_PREFIX
        self.gcs_acl = settings.GCS_ACL
    
    def get_default_destinations(self, user_id: str = None, job_id: str = None) -> List[Dict[str, Any]]:
        """
        Retorna a configuração padrão de destinos
        
        NOTA: Shotstack confirmou que não suporta destinations customizados.
        Usamos apenas Shotstack CDN e transferimos automaticamente para GCS.
        
        Args:
            user_id: ID do usuário (opcional, para organização)
            job_id: ID do job (opcional, para nomeação única)
        
        Returns:
            Lista de destinos configurados (apenas Shotstack CDN)
        """
        destinations = []
        
        # Usar apenas Shotstack CDN (único suportado)
        shotstack_destination = {
            "provider": "shotstack",
            "exclude": False
        }
        destinations.append(shotstack_destination)
        
        return destinations
    
    def _generate_gcs_path(self, user_id: str = None, job_id: str = None) -> str:
        """
        Gera um caminho organizado para o arquivo no GCS
        
        Estrutura: videos/{ano}/{mes}/{user_id}/video_{job_id}
        """
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # Caminho base
        path_parts = [self.gcs_path_prefix, year, month]
        
        # Adicionar user_id se disponível
        if user_id:
            path_parts.append(f"user_{user_id}")
        
        # Nome do arquivo - apenas job_id
        filename = f"video_{job_id}" if job_id else f"video_{now.strftime('%Y%m%d_%H%M%S')}"
        path_parts.append(filename)
        
        return "/".join(path_parts)
    
    def get_gcs_public_url(self, gcs_path: str, bucket: str = None) -> str:
        """
        Constrói a URL pública do Google Cloud Storage
        
        Args:
            gcs_path: Caminho do arquivo no GCS
            bucket: Nome do bucket (usa o padrão se não informado)
        
        Returns:
            URL pública do arquivo
        """
        bucket_name = bucket or self.gcs_bucket
        
        # URL pública padrão do GCS
        return f"https://storage.googleapis.com/{bucket_name}/{gcs_path}.mp4"
    
    def extract_gcs_url_from_response(self, shotstack_response: Dict[str, Any]) -> str:
        """
        Extrai a URL do GCS da resposta do Shotstack
        
        Args:
            shotstack_response: Resposta completa da API Shotstack
            
        Returns:
            URL do vídeo no GCS ou None se não encontrada
        """
        # Verificar no campo destinations da resposta
        destinations = shotstack_response.get("destinations", [])
        
        for dest in destinations:
            if dest.get("provider") == "googlecloudstorage":
                # Verificar múltiplos campos possíveis
                url = (dest.get("url") or 
                       dest.get("output_url") or 
                       dest.get("download_url") or
                       dest.get("file_url"))
                
                if url:
                    return url
                
                # Se não tem URL direta, tentar construir a partir do path
                if dest.get("options", {}).get("path"):
                    path = dest["options"]["path"]
                    bucket = dest["options"].get("bucket", self.gcs_bucket)
                    return self.get_gcs_public_url(path, bucket)
        
        return None
    
    async def transfer_to_gcs(self, shotstack_url: str, user_id: str, job_id: str) -> str:
        """
        Transfere um vídeo do Shotstack CDN para Google Cloud Storage
        
        Args:
            shotstack_url: URL do vídeo no Shotstack CDN
            user_id: ID do usuário
            job_id: ID do job
            
        Returns:
            URL pública do arquivo no GCS
        """
        import httpx
        import os
        from google.cloud import storage
        from google.oauth2 import service_account
        
        try:
            logger.info(f"Starting transfer: {shotstack_url} -> GCS")
            
            # Gerar path para GCS
            gcs_path = self._generate_gcs_path(user_id, job_id)
            gcs_filename = f"{gcs_path}.mp4"
            
            logger.info(f"GCS destination: gs://{self.gcs_bucket}/{gcs_filename}")
            
            # Baixar arquivo do Shotstack
            logger.info("Downloading video from Shotstack...")
            async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minutos timeout
                response = await client.get(shotstack_url)
                response.raise_for_status()
                video_content = response.content
                
            video_size_mb = len(video_content) / (1024 * 1024)
            logger.info(f"Downloaded {video_size_mb:.2f} MB from Shotstack")
            
            # Configurar cliente GCS usando credenciais do arquivo ou ambiente
            # Primeiro tentar a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(credentials_path)
                client = storage.Client(credentials=credentials, project=credentials.project_id)
            else:
                # Fallback para credenciais padrão do ambiente
                client = storage.Client()
            
            bucket = client.bucket(self.gcs_bucket)
            blob = bucket.blob(gcs_filename)
            
            # Upload para GCS
            logger.info("Uploading to Google Cloud Storage...")
            blob.upload_from_string(
                video_content, 
                content_type='video/mp4'
            )
            
            # Note: ACL não configurado devido ao uniform bucket-level access
            # O bucket deve estar configurado para acesso público
            logger.info("Upload completed - bucket should have public access configured")
            
            # Retornar URL pública
            gcs_url = self.get_gcs_public_url(gcs_path)
            logger.info(f"Transfer completed successfully: {gcs_url}")
            
            return gcs_url
            
        except Exception as e:
            logger.error(f"Failed to transfer video to GCS: {str(e)}")
            import traceback
            logger.error(f"Transfer error details: {traceback.format_exc()}")
            
            # Re-lançar a exceção para que seja tratada pelo job
            raise e