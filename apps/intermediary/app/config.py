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
    
    class Config:
        env_file = ".env"

settings = Settings()