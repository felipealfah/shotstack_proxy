# BUSINESS RULES - Shotstack Intermediary Platform

## 📋 Visão Geral

Este documento define as regras de negócio específicas para a plataforma intermediária Shotstack. Use estas regras como base para implementação de código, validações e lógica de negócio.

## 👤 Gestão de Usuários

### Registro e Autenticação
- **Registro**: Email + senha (mínimo 6 caracteres)
- **Verificação**: Email de verificação obrigatório antes do primeiro uso
- **Perfil**: Nome, email, data de criação são armazenados
- **Sessão**: JWT tokens gerenciados pelo Supabase Auth
- **Saldo Inicial**: Todo usuário novo recebe 0 tokens automaticamente

### Estados do Usuário
- **Ativo**: Pode usar todos os recursos da plataforma
- **Não Verificado**: Não pode gerar API keys ou fazer renderizações
- **Suspenso**: Acesso bloqueado (implementação futura)

## 🔑 Sistema de API Keys

### Geração de API Keys
- **Formato**: `sk_` + 64 caracteres hexadecimais
- **Nome**: Obrigatório, máximo 50 caracteres, único por usuário
- **Armazenamento**: Apenas hash SHA-256 é salvo no banco
- **Exibição**: Chave completa mostrada apenas UMA vez na criação
- **Limite**: Máximo 10 API keys ativas por usuário

### Validação e Segurança
- **Autenticação**: Bearer token no header `Authorization`
- **Validação**: FastAPI → Supabase (service role)
- **Rate Limiting**: 100 requests/hora por API key (configurável)
- **Logs**: Toda requisição é registrada com timestamp e endpoint
- **Revogação**: Usuário pode desativar/deletar keys a qualquer momento

### Estados da API Key
- **Ativa**: Pode fazer requisições normalmente
- **Inativa**: Não aceita requisições (retorna 401)
- **Deletada**: Removida permanentemente do sistema

## 💰 Sistema de Tokens

### Economia de Tokens
- **Unidade Base**: 1 token = 1 minuto de video, ou seja, 1 token deve ser igual a 60 segundos
- **Consumo**: Tokens são debitados ANTES da renderização
- **Falha**: Se renderização falhar, tokens são reembolsados automaticamente
- **Saldo Mínimo**: Usuário precisa ter pelo menos 1 token para renderizar
- **Saldo Negativo**: Não permitido - transações são rejeitadas

### Pacotes de Tokens (Stripe)

## Sistema de Renderização

### Validações de Request
- **Autenticação**: API key válida e ativa obrigatória
- **Saldo**: Usuário deve ter tokens suficientes
- **Rate Limit**: Respeitado por API key
- **Payload**: JSON válido conforme schema Shotstack
- **Tamanho**: Máximo 10MB por request

### Fluxo de Renderização
1. **Recepção**: FastAPI recebe request com timeline JSON
2. **Validação**: API key + saldo + rate limit + payload
3. **Débito**: Tokens são debitados imediatamente
4. **Enfileiramento**: Job adicionado na fila Redis
5. **Processamento**: Worker pega job e envia para Shotstack
6. **Monitoramento**: Worker verifica status periodicamente
7. **Transferência**: Vídeo pronto → transferido para GCS
8. **Notificação**: Status atualizado para "completed"

### Estados da Renderização
- **queued**: Na fila aguardando processamento
- **processing**: Sendo processado pela Shotstack
- **completed**: Finalizado e disponível no GCS
- **failed**: Falhou (tokens são reembolsados)
- **cancelled**: Cancelado pelo usuário

### Políticas de Reembolso
- **Falha Técnica**: Reembolso automático imediato
- **Falha de Payload**: Sem reembolso (erro do usuário)
- **Cancelamento**: Reembolso se ainda não iniciado processamento
- **Timeout**: Reembolso automático após 30 minutos sem resposta

## Sistema de Analytics e Usage

### Logs de Uso
- **Obrigatório**: Toda chamada à API é logada
- **Dados**: User ID, API key, endpoint, tokens consumidos, timestamp
- **Retenção**: Logs mantidos por 12 meses
- **Agregação**: Estatísticas diárias/mensais por usuário

### Métricas Disponíveis
- **Dashboard Usuário**:
  - Saldo atual de tokens
  - Uso nos últimos 30 dias
  - Top 5 endpoints mais usados
  - Histórico de renderizações
  - Gráfico de uso ao longo do tempo

### Limites e Quotas
- **Rate Limiting**: 100 req/hora por API key (configurável)
- **Concurrent Jobs**: Máximo 5 renderizações simultâneas por usuário

## 🔄 Integração com APIs Externas

### Shotstack API
- **Autenticação**: x-api-key header (nossa chave mestra)
- **Retry Policy**: 3 tentativas com backoff exponencial
- **Timeout**: 30 segundos por request
- **Webhook**: Configurado para notificar status changes
- **Fallback**: Polling de status se webhook falhar

### Google Cloud Storage
- **Bucket**: Configurado com acesso público de leitura
- **Path Structure**: `videos/{year}/{month}/{user_id}/video_{job_id}.mp4`
- **Retention**: Arquivos mantidos permanentemente
- **Access**: URLs públicas geradas automaticamente
- **Backup**: Não implementado (Shotstack mantém por 24h)

## Stripe Webhooks


## Tratamento de Erros

### Códigos de Erro Padronizados
```javascript
const ERROR_CODES = {
  // Autenticação
  INVALID_API_KEY: { code: 401, message: "API key inválida ou inativa" },
  MISSING_AUTH: { code: 401, message: "Authorization header obrigatório" },
  
  // Tokens
  INSUFFICIENT_TOKENS: { code: 402, message: "Saldo insuficiente de tokens" },
  TOKEN_DEBIT_FAILED: { code: 500, message: "Falha ao debitar tokens" },
  
  // Rate Limiting  
  RATE_LIMIT_EXCEEDED: { code: 429, message: "Limite de requisições excedido" },
  
  // Payload
  INVALID_PAYLOAD: { code: 400, message: "JSON inválido ou malformado" },
  PAYLOAD_TOO_LARGE: { code: 413, message: "Payload excede 10MB" },
  
  // Renderização
  RENDER_FAILED: { code: 500, message: "Falha na renderização" },
  JOB_NOT_FOUND: { code: 404, message: "Job de renderização não encontrado" }
}
```

### Política de Retry
- **API Keys**: Não retry (erro permanente)
- **Tokens**: Não retry (pode causar dupla cobrança)
- **Shotstack**: 3 tentativas com backoff (2s, 4s, 8s)
- **GCS Upload**: 5 tentativas com backoff (1s, 2s, 4s, 8s, 16s)

## 📈 Métricas de Negócio

### KPIs Principais
- **Revenue**: Total de tokens vendidos por mês
- **Churn**: Usuários que não usaram tokens em 30 dias
- **Usage**: Média de tokens consumidos por usuário
- **Success Rate**: % de renderizações bem-sucedidas
- **Response Time**: Tempo médio de renderização

### Alertas Automáticos
- **High Error Rate**: >5% de falhas em 1 hora
- **Low Balance**: Usuário com <3 tokens
- **API Abuse**: >200 req/hora de uma API key
- **Webhook Failures**: >10 webhooks falharam em 1 hora

## 🔒 Regras de Segurança

### Proteção de Dados
- **PII**: Apenas email é armazenado como PII
- **API Keys**: Apenas hash SHA-256 armazenado
- **Logs**: IPs não são armazenados por privacidade
- **GDPR**: Usuários podem exportar/deletar dados

### Rate Limiting Avançado
- **Global**: 1000 req/min para todo o sistema
- **Por IP**: 60 req/min por IP (proteção DDoS)
- **Por User**: 100 req/hora por usuário
- **Por API Key**: 100 req/hora por key

### Validações de Segurança
- **SQL Injection**: Todas queries via ORM/prepared statements
- **XSS**: Sanitização de inputs no frontend
- **CSRF**: Tokens CSRF em formulários
- **Headers**: Security headers obrigatórios (CORS, CSP, etc.)

## 🚀 Regras de Performance

### Cache Strategy
- **API Keys**: Cache por 5 minutos após validação
- **Token Balance**: Cache por 1 minuto
- **User Profile**: Cache por 10 minutos
- **Usage Stats**: Cache por 1 hora

### Otimizações
- **DB Queries**: Índices em user_id, api_key_hash, created_at
- **File Upload**: Streaming upload para GCS
- **Background Jobs**: Processamento assíncrono obrigatório
- **CDN**: Assets estáticos via CDN (futuro)

## 📝 Notas de Implementação

### Prioridades de Desenvolvimento
1. **P0 (Crítico)**: Auth, API keys, renderização básica
2. **P1 (Alto)**: Tokens, pagamentos, webhooks
3. **P2 (Médio)**: Analytics, dashboard avançado
4. **P3 (Baixo)**: Relatórios, exportações

### Configurações por Ambiente
- **Development**: Rate limits relaxados, logs verbosos
- **Staging**: Configurações de produção, dados de teste
- **Production**: Rate limits rigorosos, monitoramento ativo

---

**📌 Nota**: Este documento deve ser atualizado sempre que novas regras de negócio forem definidas ou modificadas. Todas as implementações devem seguir estritamente estas regras.