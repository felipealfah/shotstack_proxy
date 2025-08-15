from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv
from arq import create_pool
from arq.connections import RedisSettings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging

from .config import settings
from .routers import shotstack, health, expiration, gcp_sync
from .middleware.auth import verify_api_key
from .middleware.rate_limit import RateLimitMiddleware
from .services.expiration_service import run_expiration_sync, run_cleanup
from .services.gcp_sync_service import run_gcp_sync_fallback

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(api_app: FastAPI):
    # Startup: Create Redis connection pool
    api_app.state.redis_pool = await create_pool(
        RedisSettings.from_dsn(settings.REDIS_URL)
    )
    
    # Startup: Initialize and start scheduler for video expiration
    scheduler = AsyncIOScheduler()
    
    # Run expiration sync (configurável via ENV)
    scheduler.add_job(
        run_expiration_sync,
        'cron',
        hour=settings.EXPIRATION_SYNC_CRON_HOURS,
        minute=0,
        id='expiration_sync',
        replace_existing=True
    )
    
    # Run cleanup of old records once daily (configurável via ENV)
    scheduler.add_job(
        run_cleanup,
        'cron',
        hour=settings.CLEANUP_JOB_CRON_HOUR,
        minute=0,
        id='cleanup_old_records',
        replace_existing=True
    )
    
    # Run GCP sync fallback every hour (configurável via ENV)
    if settings.GCP_SYNC_ENABLED:
        scheduler.add_job(
            run_gcp_sync_fallback,
            'cron',
            minute=0,
            id='gcp_sync_fallback',
            replace_existing=True
        )
        logger.info("GCP sync fallback cron job enabled")
    else:
        logger.info("GCP sync fallback is disabled via GCP_SYNC_ENABLED=false")
    
    scheduler.start()
    api_app.state.scheduler = scheduler
    logger.info(f"Schedulers started - Expiration sync: {settings.EXPIRATION_SYNC_CRON_HOURS}h, Cleanup: {settings.CLEANUP_JOB_CRON_HOUR}h, GCP Sync: hourly")
    
    yield
    
    # Shutdown: Stop scheduler and close Redis connection
    scheduler.shutdown()
    await api_app.state.redis_pool.close()
    logger.info("Application shutdown complete")

# This is the sub-application that contains all the API logic
api_app = FastAPI(
    title="🎬 Aion Videos API",
    description="""
    ## 🚀 API Completa para Renderização de Vídeos
    
    **Plataforma profissional Aion Videos** para criação de vídeos de alta qualidade, 
    com transferência automática para Google Cloud Storage e sistema baseado em tokens.
    
    ### 🎯 Principais Funcionalidades:
    - ⚡ **Renderização Individual**: Crie vídeos únicos rapidamente
    - 📦 **Renderização em Lote**: Processe múltiplos vídeos simultaneamente  
    - 🤖 **Integração N8N**: Workflows automatizados para produção em escala
    - ☁️ **Storage Automático**: Vídeos transferidos automaticamente para GCS
    - 💰 **Sistema de Tokens**: Cobrança baseada em uso
    - ⏱️ **Expiração 48h**: Gestão automática do ciclo de vida dos vídeos
    
    ### 📋 Endpoints Principais:
    - `POST /v1/render` - Renderização individual  
    - `POST /v1/batch-render-array` - Renderização em lote (otimizado para N8N)
    - `GET /v1/videos/{job_id}` - Download e acesso aos vídeos
    - `GET /v1/job/{job_id}` - Status de processamento
    
    ### 🎬 Workflow Típico:
    1. **Autenticação**: Use sua API Key no header `Authorization: Bearer YOUR_KEY`
    2. **Renderização**: Envie payload com timeline/assets/output
    3. **Monitoramento**: Aguarde 30s-2min para processamento
    4. **Download**: Acesse vídeo via URL do Google Cloud Storage
    
    ### 📞 Suporte:
    - 📧 Email: support@videoapi.com
    - 📚 Documentação: Consulte os exemplos interativos abaixo
    - 🐛 Issues: Reporte problemas através do sistema
    """,
    version="2.0.0",
    lifespan=lifespan,
    contact={
        "name": "Aion Videos Support Team",
        "email": "support@aionvideos.com",
        "url": "https://aionvideos.com/support"
    },
    license_info={
        "name": "Commercial License",
        "url": "https://aionvideos.com/license"
    },
    terms_of_service="https://aionvideos.com/terms",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "deepLinking": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "operationsSorter": "method",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "tryItOutEnabled": True
    }
)

# Mount static files for custom CSS and assets
api_app.mount("/static", StaticFiles(directory="static"), name="static")

# Custom Swagger UI with CSS
@api_app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.css" />
        <link type="text/css" rel="stylesheet" href="/static/css/swagger-custom.css" />
        <title>🎬 Aion Videos API - Interactive Documentation</title>
        <link rel="icon" type="image/x-icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">
        <meta name="viewport" content="width=device-width, initial-scale=1">
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
        <script>
        const ui = SwaggerUIBundle({
            url: '/api/openapi.json', // Correct URL for the mounted app
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.presets.standalone
            ],
            layout: "StandaloneLayout",
            docExpansion: "list",
            operationsSorter: "method",
            filter: true,
            showExtensions: true,
            showCommonExtensions: true,
            tryItOutEnabled: true,
            displayRequestDuration: true,
            persistAuthorization: true,
            supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
            validatorUrl: null,
            onComplete: function() {
                // Add custom header message
                const infoElement = document.querySelector('.swagger-ui .info');
                if (infoElement) {
                    const customHeader = document.createElement('div');
                    customHeader.innerHTML = `
                        <div style="background: linear-gradient(135deg, #0066cc 0%, #004499 100%); color: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                            <h3 style="margin: 0; color: white;">🚀 Ready to Start?</h3>
                            <p style="margin: 10px 0 0 0; opacity: 0.9;">Use the interactive examples below to test our API endpoints directly!</p>
                        </div>
                    `;
                    infoElement.appendChild(customHeader);
                }
            }
        });
        </script>
    </body>
    </html>
    """)

# CORS middleware
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
api_app.add_middleware(RateLimitMiddleware)

# Include routers
api_app.include_router(health.router, prefix="/health", tags=["health"])

# Main video rendering router with authentication
api_app.include_router(
    shotstack.router, 
    prefix="/v1", 
    tags=["video-rendering"]
)

# Video expiration management router
api_app.include_router(
    expiration.router, 
    prefix="/v1", 
    tags=["expiration"]
)

# GCP sync fallback router (hidden from documentation)
api_app.include_router(
    gcp_sync.router, 
    prefix="/v1", 
    tags=["gcp-sync"],
    include_in_schema=False
)

@api_app.get("/")
async def root():
    return {"message": "Aion Videos API", "version": "2.0.0"}

# This is the main application that will be run by Uvicorn
app = FastAPI()
app.mount("/api", api_app)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )
