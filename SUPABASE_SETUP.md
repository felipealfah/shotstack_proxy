# Supabase Setup Guide

Este guia fornece instruções detalhadas para configurar o Supabase para o projeto Shotstack Intermediary Platform.

## 🚀 1. Criar Projeto Supabase

1. Acesse [https://supabase.com](https://supabase.com)
2. Faça login ou crie uma conta
3. Clique em "New Project"
4. Escolha uma organização
5. Configure o projeto:
   - **Name**: `shotstack-intermediary` (ou nome de sua preferência)
   - **Database Password**: Gere uma senha forte (salve em local seguro!)
   - **Region**: Escolha a região mais próxima dos seus usuários
6. Clique em "Create new project"

⏱️ **Aguarde 2-5 minutos** para o projeto ser criado.

## 🔑 2. Obter Credenciais da API

1. No dashboard do seu projeto, vá para **Settings > API**
2. Copie as seguintes informações:

```bash
# Project URL
NEXT_PUBLIC_SUPABASE_URL=https://seu-project-id.supabase.co

# Anon/Public Key (para o frontend)
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Service Role Key (para operações administrativas)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 🗄️ 3. Obter String de Conexão do Banco

1. Vá para **Settings > Database**
2. Na seção "Connection string", selecione **Pooler**
3. Copie a connection string:

```bash
DATABASE_URL=postgresql://postgres.seu-project-id:[SUA-SENHA]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**⚠️ Importante**: Substitua `[SUA-SENHA]` pela senha que você criou no passo 1.

## 📋 4. Executar Schema SQL

1. No dashboard, vá para **SQL Editor**
2. Clique em "New Query"
3. Copie todo o conteúdo do arquivo `scripts/supabase-schema.sql`
4. Cole no editor SQL
5. Clique em "Run" para executar

### Verificar se funcionou:

1. Vá para **Table Editor**
2. Você deve ver as seguintes tabelas:
   - `api_keys`
   - `credit_balance`
   - `usage_logs`
   - `renders`
   - `stripe_customers`

## 🔐 5. Configurar Autenticação

1. Vá para **Authentication > Settings**
2. Configure os provedores desejados:

### Email/Password (Padrão)
- Já está habilitado por padrão
- Configure templates de email se necessário

### Google OAuth (Opcional)
1. Em "Auth Providers", habilite Google
2. Configure Client ID e Client Secret do Google
3. Adicione URLs de redirect:
   - Development: `http://localhost:3000/auth/callback`
   - Production: `https://seudominio.com/auth/callback`

### GitHub OAuth (Opcional)
1. Em "Auth Providers", habilite GitHub
2. Configure Client ID e Client Secret do GitHub
3. Configure URLs de redirect similares ao Google

## 🔒 6. Configurar Row Level Security (RLS)

As políticas RLS já foram criadas pelo schema SQL, mas você pode verificar:

1. Vá para **Authentication > Policies**
2. Verifique se existem políticas para todas as tabelas
3. As políticas garantem que:
   - Usuários só acessam seus próprios dados
   - Service role pode fazer operações administrativas

## ⚙️ 7. Configurar Variáveis de Ambiente

1. Copie o arquivo `.env.example` para `.env`
2. Preencha com as credenciais obtidas:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://seu-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua-anon-key
SUPABASE_SERVICE_ROLE_KEY=sua-service-role-key
DATABASE_URL=postgresql://postgres.seu-project-id:senha@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

## 🧪 8. Testar a Configuração

### Método 1: Via aplicação
```bash
docker-compose up -d
curl http://localhost:3000/api/health
```

### Método 2: Via SQL Editor
Execute no SQL Editor do Supabase:
```sql
-- Testar se as tabelas existem
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Testar se RLS está ativo
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public';
```

## 🔄 9. Gerar Types TypeScript (Opcional)

1. Install Supabase CLI:
```bash
npm install -g supabase
```

2. Login no Supabase:
```bash
supabase login
```

3. Gerar types:
```bash
supabase gen types typescript --project-id=seu-project-id > src/types/supabase.ts
```

## 📊 10. Configurar Realtime (Opcional)

Para atualizações em tempo real:

1. Vá para **Database > Replication**
2. Habilite replication para as tabelas desejadas:
   - `credit_balance` (para saldo em tempo real)
   - `renders` (para status de renderização)

## 🚨 Troubleshooting

### Erro: "Invalid API key"
- Verifique se copiou as keys corretamente
- Confirme que não há espaços extras

### Erro: "Connection refused"
- Verifique a string de conexão
- Confirme que a senha está correta
- Teste conexão via psql:
```bash
psql "postgresql://postgres.seu-project-id:senha@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

### Erro: "RLS policy violation"
- Verifique se as políticas RLS foram criadas
- Confirme que está usando o service role key para operações administrativas

### Tabelas não aparecem
- Execute novamente o schema SQL
- Verifique se não há erros na execução
- Confirme que está logado como owner do projeto

## 📚 Recursos Adicionais

- [Supabase Documentation](https://supabase.com/docs)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [API Reference](https://supabase.com/docs/reference/javascript/introduction)

## ✅ Checklist Final

- [ ] Projeto Supabase criado
- [ ] Credenciais API copiadas
- [ ] Schema SQL executado com sucesso
- [ ] Tabelas criadas (5 tabelas visíveis)
- [ ] RLS policies ativas
- [ ] Variáveis de ambiente configuradas
- [ ] Teste de conexão bem-sucedido
- [ ] Aplicação rodando sem erros de database

Após completar todos os itens, seu Supabase está pronto para uso! 🎉