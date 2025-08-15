#!/bin/bash

echo "🚀 Deploy Aion Videos na VPS..."

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para log colorido
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se está no diretório correto
if [ ! -f "docker-compose.yml" ]; then
    error "Arquivo docker-compose.yml não encontrado!"
    error "Execute este script na raiz do projeto."
    exit 1
fi

log "Parando containers existentes..."
docker-compose down 2>/dev/null || true

log "Atualizando código do Git..."
git pull origin main

log "Limpando imagens antigas..."
docker-compose down --rmi all --volumes --remove-orphans 2>/dev/null || true

log "Buildando todos os containers (isso pode demorar alguns minutos)..."
if docker-compose build --no-cache --parallel; then
    success "Build concluído com sucesso!"
else
    error "Falha no build dos containers!"
    exit 1
fi

log "Subindo aplicação completa..."
if docker-compose up -d; then
    success "Aplicação iniciada!"
else
    error "Falha ao iniciar aplicação!"
    exit 1
fi

log "Aguardando containers ficarem prontos..."
sleep 15

log "Verificando status dos containers..."
docker-compose ps

# Verificar se todos os containers essenciais estão rodando
CONTAINERS=(redis api worker web)
ALL_HEALTHY=true

for container in "${CONTAINERS[@]}"; do
    if docker-compose ps | grep -q "${container}.*Up"; then
        success "Container $container: Running"
    else
        error "Container $container: Failed"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = true ]; then
    echo ""
    success "🎉 Deploy concluído com sucesso!"
    echo ""
    echo "📱 Aplicação disponível em:"
    echo "   🌐 Frontend: http://$(curl -s ifconfig.me):3003"
    echo "   🔧 API: http://$(curl -s ifconfig.me):8002"
    echo "   📚 Docs: http://$(curl -s ifconfig.me):8002/docs"
    echo ""
    log "Para ver logs em tempo real: docker-compose logs -f"
else
    echo ""
    warning "Alguns containers podem ter problemas. Verifique os logs:"
    echo "   docker-compose logs -f"
fi

echo ""
log "Deploy finalizado!"