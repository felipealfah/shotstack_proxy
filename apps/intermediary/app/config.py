from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SHOTSTACK_API_KEY: str
    SHOTSTACK_API_URL: str = "https://api.shotstack.io/v1"
    REDIS_URL: str = "redis://localhost:6379"
    WEB_SERVICE_URL: str = "http://localhost:3000"
    JWT_SECRET: str
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