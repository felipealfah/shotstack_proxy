# FastAPI Backend - Rotas e Integração

## Visão Geral da API

A API FastAPI funciona como um intermediário entre o frontend React e os serviços Shotstack, com sistema de autenticação baseado em tokens e API keys. Todas as requisições são processadas por workers Redis em background.

**Base URL**: `http://localhost:8001` (desenvolvimento)

## Autenticação

A API suporta dois tipos de autenticação:

### 1. API Keys (Recomendado para integração programática)
```
Authorization: Bearer sk_test_1234567890abcdef...
```

### 2. JWT Tokens (Supabase Auth para frontend)
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Endpoints Disponíveis

### 🔧 Health Check
```http
GET /health/
```
**Resposta:**
```json
{
  "status": "healthy",
  "redis": "healthy", 
  "shotstack_config": "configured"
}
```

### 🎬 Video Rendering

#### 1. Criar Render
```http
POST /api/v1/render
Content-Type: application/json
Authorization: Bearer {api_key_or_jwt}

{
  "timeline": {
    "soundtrack": {...},
    "background": "#000000",
    "tracks": [...]
  },
  "output": {
    "format": "mp4",
    "resolution": "hd"
  },
  "destinations": [
    {
      "provider": "googlecloudstorage",
      "options": {
        "bucket": "my-bucket",
        "path": "/videos/"
      }
    }
  ],
  "webhook": "https://myapp.com/webhook"
}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Render job queued successfully",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "estimated_tokens": 1
}
```

#### 2. Status do Job
```http
GET /api/v1/job/{job_id}
Authorization: Bearer {api_key_or_jwt}
```

**Resposta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "result": {
    "status": "success",
    "shotstack_render_id": "2abd5c11-0f3d-42c6-9676-a745c717c66a",
    "user_id": "user_123"
  },
  "error": null
}
```

#### 3. Status do Render Shotstack
```http
GET /api/v1/render/{shotstack_render_id}
Authorization: Bearer {api_key_or_jwt}
```

#### 4. Links do Vídeo (Download)
```http
GET /api/v1/videos/{job_id}
Authorization: Bearer {api_key_or_jwt}
```

**Resposta:**
```json
{
  "success": true,
  "message": "Video rendered successfully",
  "video_url": "https://storage.googleapis.com/my-bucket/videos/user_123/550e8400-e29b-41d4-a716-446655440000.mp4",
  "poster_url": "https://shotstack-cdn.com/stage/2abd5c11-0f3d-42c6-9676-a745c717c66a-00-00.jpg",
  "thumbnail_url": "https://shotstack-cdn.com/stage/2abd5c11-0f3d-42c6-9676-a745c717c66a-thumb.jpg",
  "render_id": "2abd5c11-0f3d-42c6-9676-a745c717c66a",
  "transfer_status": "completed"
}
```

#### 5. Webhook Shotstack
```http
POST /api/v1/webhook
Content-Type: application/json

{
  "type": "render",
  "action": "complete",
  "id": "2abd5c11-0f3d-42c6-9676-a745c717c66a",
  "render": {
    "status": "done",
    "url": "https://shotstack-cdn.com/stage/2abd5c11-0f3d-42c6-9676-a745c717c66a.mp4"
  }
}
```

## Fluxo de Trabalho

### 1. Renderização de Vídeo
```
Frontend → POST /api/v1/render → Redis Queue → Shotstack API → GCS Transfer
```

1. **Frontend** envia requisição com timeline do vídeo
2. **FastAPI** valida autenticação e tokens
3. **Job** é enfileirado no Redis para processamento
4. **Worker** processa o job e envia para Shotstack
5. **Shotstack** renderiza o vídeo
6. **Worker** transfere vídeo para Google Cloud Storage
7. **Frontend** consulta status e obtém links

### 2. Consulta de Status
```
Frontend → GET /api/v1/job/{id} → Redis → Status Response
Frontend → GET /api/v1/videos/{id} → GCS URLs
```

## Integração Frontend

### Exemplo de Hook React
```typescript
// hooks/useVideoRender.ts
export function useVideoRender() {
  const { token } = useAuth()
  
  const createRender = async (timeline: Timeline) => {
    const response = await fetch('/api/v1/render', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ timeline, output: { format: 'mp4' } })
    })
    
    return response.json()
  }
  
  const getJobStatus = async (jobId: string) => {
    const response = await fetch(`/api/v1/job/${jobId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  }
  
  const getVideoLinks = async (jobId: string) => {
    const response = await fetch(`/api/v1/videos/${jobId}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  }
  
  return { createRender, getJobStatus, getVideoLinks }
}
```

## Tratamento de Erros

### Códigos de Status
- **200**: Sucesso
- **401**: Não autorizado (API key/JWT inválido)  
- **402**: Tokens insuficientes
- **404**: Job/Render não encontrado
- **500**: Erro interno do servidor
- **503**: Serviço indisponível (Redis/DB offline)

### Exemplo de Resposta de Erro
```json
{
  "detail": "Insufficient tokens. Please purchase more tokens."
}
```

## Configurações Importantes

### Environment Variables (.env)
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Shotstack  
SHOTSTACK_API_KEY=your-shotstack-key
SHOTSTACK_API_URL=https://api.shotstack.io/v1

# Redis
REDIS_URL=redis://localhost:6379

# Google Cloud Storage
GCS_BUCKET=your-gcs-bucket
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Workers Redis
Os seguintes jobs são processados em background:
- `render_video_job`: Processa renderização no Shotstack
- `check_render_status_job`: Verifica status de renders
- `transfer_video_to_gcs_job`: Transfere vídeos para GCS

## Banco de Dados (Supabase)

### Tabelas Principais
- **users**: Perfis de usuários e saldo de tokens
- **api_keys**: Chaves de API para acesso programático  
- **renders**: Histórico de renderizações
- **usage_logs**: Logs de uso da API

## Sistema de Tokens
- Cada renderização consome **1 token**
- Tokens são validados antes do processamento
- Saldo é atualizado em tempo real
- Logs de uso são registrados para cobrança

## Desenvolvimento e Debug
- **Swagger UI**: `http://localhost:8001/docs`
- **Health Check**: `http://localhost:8001/health/`
- **Logs**: Disponíveis no console FastAPI
- **Redis Monitoring**: Use `redis-cli monitor`