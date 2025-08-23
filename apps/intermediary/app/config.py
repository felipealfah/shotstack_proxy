from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database configuration (Supabase PostgreSQL)
    DATABASE_URL: str
    
    # Supabase configuration
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Shotstack API configuration
    SHOTSTACK_API_KEY: str
    SHOTSTACK_API_URL: str = "https://api.shotstack.io/v1"
    
    # Redis configuration
    REDIS_URL: str = "redis://localhost:6379"
    
    # FastAPI server configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ENVIRONMENT: str = "development"
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600  # 1 hour in seconds
    
    # Google Cloud Storage settings
    GCS_BUCKET: str = "ffmpeg-api"  # Seu bucket padrão
    GCS_PATH_PREFIX: str = "videos"  # Prefixo para organizar os arquivos
    GCS_ACL: str = "publicRead"  # Permissão pública para leitura
    
    # Cron Job Configuration (Issue #9)
    EXPIRATION_SYNC_CRON_HOURS: str = "*/6"  # Sincronização de expiração
    CLEANUP_JOB_CRON_HOUR: int = 3  # Hora do cleanup diário
    
    # Video Lifecycle Configuration (Issue #9)
    VIDEO_RETENTION_DAYS: int = 2  # Tempo de retenção de vídeos (dias)
    DB_RECORD_CLEANUP_DAYS: int = 30  # Limpeza de registros antigos (dias)
    
    # API Timeout Configuration (Issue #9)
    SHOTSTACK_API_TIMEOUT_SECONDS: float = 10.0  # Timeout para Shotstack API
    GCS_HEAD_REQUEST_TIMEOUT_SECONDS: float = 5.0  # Timeout para verificação GCS
    USER_VIDEOS_PAGE_LIMIT: int = 20  # Limite de vídeos por página
    
    # GCP Video Sync Fallback Configuration (Issue #11)
    GCP_SYNC_ENABLED: bool = True  # Habilitar sistema de fallback
    GCP_SYNC_RETENTION_DAYS: int = 7  # Quantos dias para trás verificar
    GCP_SYNC_LOG_LEVEL: str = "INFO"  # Log level para sincronização
    
    # Dual Authentication Configuration (Email + API Key Security)
    DUAL_AUTH_ENABLED: bool = True  # Habilitar validação dupla
    DUAL_AUTH_STRICT_MODE: bool = False  # Modo strict (sem fallback para API key simples)
    DUAL_AUTH_LOG_ATTEMPTS: bool = True  # Log tentativas de acesso
    
    # Payload Validation Configuration (Issue #15)
    VALIDATION_ENABLED: bool = True  # Feature flag para validação de payload
    SANITIZATION_ENABLED: bool = True  # Auto-fix common issues (string nulls, etc)
    VALIDATION_STRICT_MODE: bool = False  # Reject vs sanitize problematic payloads
    VALIDATION_LOG_FAILURES: bool = True  # Log validation failures for debugging
    VALIDATION_TIMEOUT_MS: int = 100  # Max validation time in milliseconds
    
    class Config:
        env_file = ".env"

settings = Settings()