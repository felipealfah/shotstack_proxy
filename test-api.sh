#!/bin/bash

# Script de teste da API
# Uso: ./test-api.sh <API_KEY>

if [ -z "$1" ]; then
    echo "❌ Uso: $0 <API_KEY>"
    echo "Exemplo: $0 sk_live_abcd1234..."
    exit 1
fi

API_KEY="$1"
BASE_URL="http://localhost:8001"

echo "🧪 Testando API Shotstack Intermediary..."
echo "📡 Base URL: $BASE_URL"
echo "🔑 API Key: ${API_KEY:0:20}..."
echo ""

# 1. Teste de Health Check
echo "1️⃣ Testando Health Check..."
curl -s "$BASE_URL/health/" | jq '.'
echo ""

# 2. Teste de autenticação com API key inválida
echo "2️⃣ Testando autenticação com API key inválida..."
curl -s -X POST "$BASE_URL/api/v1/render" \
    -H "Authorization: Bearer invalid_key" \
    -H "Content-Type: application/json" \
    -d '{"test": "data"}' | jq '.'
echo ""

# 3. Teste de autenticação com API key válida
echo "3️⃣ Testando autenticação com API key válida..."
curl -s -X POST "$BASE_URL/api/v1/render" \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "timeline": {
            "soundtrack": {
                "src": "https://shotstack-assets.s3.ap-southeast-2.amazonaws.com/music/unminus/lit.mp3",
                "effect": "fadeIn"
            },
            "tracks": [
                {
                    "clips": [
                        {
                            "asset": {
                                "type": "video",
                                "src": "https://shotstack-assets.s3.ap-Southeast-2.amazonaws.com/footage/beach-overhead.mp4"
                            },
                            "start": 0,
                            "length": 5
                        }
                    ]
                }
            ]
        },
        "output": {
            "format": "mp4",
            "resolution": "sd"
        }
    }' | jq '.'

echo ""
echo "✅ Testes concluídos!"
echo ""
echo "📝 Próximos passos:"
echo "   1. Acesse http://localhost:3000 no navegador"
echo "   2. Registre um usuário"
echo "   3. Crie uma API key no dashboard"
echo "   4. Execute: ./test-api.sh <sua_api_key>"