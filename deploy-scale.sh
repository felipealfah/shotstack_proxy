#!/bin/bash

# Script de Deploy Escalável para Video Rendering Platform
# Suporta 20, 30, 50, 100+ jobs simultâneos

set -e

echo "🚀 Video Rendering Platform - Deploy Escalável"
echo "================================================"

# Função para mostrar help
show_help() {
    echo "Uso: ./deploy-scale.sh [MODO] [JOBS]"
    echo ""
    echo "MODOS DISPONÍVEIS:"
    echo "  normal         - 1 worker,  até 50 jobs  (padrão)"
    echo "  high-load      - 2 workers, até 80 jobs"  
    echo "  ultra-load     - 3 workers, até 180 jobs"
    echo "  custom         - workers customizados"
    echo ""
    echo "EXEMPLOS:"
    echo "  ./deploy-scale.sh normal                    # 50 jobs"
    echo "  ./deploy-scale.sh high-load                 # 80 jobs"
    echo "  ./deploy-scale.sh ultra-load                # 180 jobs"
    echo "  ./deploy-scale.sh custom 75                 # 75 jobs específicos"
    echo ""
    echo "MONITORAMENTO:"
    echo "  ./deploy-scale.sh status                    # Status dos workers"
    echo "  ./deploy-scale.sh logs                      # Logs em tempo real"
    echo ""
}

# Função para verificar status
check_status() {
    echo "📊 Status dos Workers:"
    echo "====================="
    
    echo "🔍 Worker 1 (Principal):"
    docker logs ss-inter-worker-1 --tail 5 2>/dev/null || echo "   ❌ Worker 1 não está rodando"
    
    echo "🔍 Worker 2 (High Load):"
    docker logs ss-inter-worker-2 --tail 5 2>/dev/null || echo "   ❌ Worker 2 não está rodando"
    
    echo "🔍 Worker 3 (Ultra Load):"
    docker logs ss-inter-worker-3 --tail 5 2>/dev/null || echo "   ❌ Worker 3 não está rodando"
    
    echo ""
    echo "📈 Jobs no Redis:"
    docker exec ss-inter-redis redis-cli info keyspace 2>/dev/null || echo "   ❌ Redis não está rodando"
}

# Função para logs em tempo real
show_logs() {
    echo "📝 Logs em tempo real (Ctrl+C para sair):"
    echo "========================================="
    
    # Logs de todos os workers disponíveis
    docker-compose logs -f worker worker-2 worker-3 2>/dev/null || docker-compose logs -f worker
}

# Parse dos argumentos
MODO=${1:-normal}
CUSTOM_JOBS=${2:-50}

case $MODO in
    "help"|"-h"|"--help")
        show_help
        exit 0
        ;;
    
    "status")
        check_status
        exit 0
        ;;
    
    "logs")
        show_logs
        exit 0
        ;;
    
    "normal")
        echo "🟢 MODO NORMAL: 1 Worker, até 50 jobs simultâneos"
        docker-compose down
        docker-compose up -d
        ;;
    
    "high-load")
        echo "🟡 MODO HIGH LOAD: 2 Workers, até 80 jobs simultâneos"
        docker-compose down
        docker-compose --profile high-load up -d
        ;;
    
    "ultra-load")
        echo "🔴 MODO ULTRA LOAD: 3 Workers, até 180 jobs simultâneos"
        docker-compose down
        docker-compose --profile ultra-high-load up -d
        ;;
    
    "custom")
        echo "⚙️  MODO CUSTOM: Jobs personalizados = $CUSTOM_JOBS"
        export ARQ_MAX_JOBS=$CUSTOM_JOBS
        docker-compose down
        docker-compose up -d
        ;;
    
    *)
        echo "❌ Modo inválido: $MODO"
        show_help
        exit 1
        ;;
esac

echo ""
echo "✅ Deploy concluído!"
echo ""
echo "🔍 Para verificar status:"
echo "   ./deploy-scale.sh status"
echo ""
echo "📝 Para ver logs:"
echo "   ./deploy-scale.sh logs"
echo ""
echo "🧪 Para testar (20 requisições):"
echo "   curl -X GET http://localhost:8002/health/"
echo ""
echo "📊 Capacidade atual configurada:"
case $MODO in
    "normal") echo "   • 1 Worker: até 50 jobs simultâneos" ;;
    "high-load") echo "   • 2 Workers: até 80 jobs simultâneos" ;;
    "ultra-load") echo "   • 3 Workers: até 180 jobs simultâneos" ;;
    "custom") echo "   • Custom: até $CUSTOM_JOBS jobs por worker" ;;
esac