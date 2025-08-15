# 🚀 Deploy na VPS - Aion Videos

## ⚡ Comando Único para Deploy

### Opção 1: Usando script automatizado
```bash
./deploy-vps.sh
```

### Opção 2: Comando docker-compose direto  
```bash
docker-compose up -d --build --force-recreate
```

### Opção 3: Comando completo manual
```bash
docker-compose down && \
docker-compose build --no-cache --parallel && \
docker-compose up -d
```

## 🔧 Configuração Inicial (primeira vez)

1. **Instalar dependências**:
```bash
# Docker
curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh

# Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Git
sudo apt update && sudo apt install -y git
```

2. **Clonar projeto**:
```bash
git clone https://github.com/SEU_USUARIO/ss_inter.git
cd ss_inter
```

3. **Criar .env**:
```bash
nano .env
```

Adicionar:
```env
# Supabase
SUPABASE_URL=https://hjwchewuibqpoeggynwp.supabase.co
SUPABASE_ANON_KEY=sua_chave_aqui
SUPABASE_SERVICE_ROLE_KEY=sua_service_key_aqui

# Shotstack
SHOTSTACK_API_KEY=sua_shotstack_key_aqui

# GCS
GCS_BUCKET=ffmpeg-api
```

4. **Configurar GCP credentials**:
```bash
nano apps/intermediary/gcp-credentials.json
```

5. **Deploy**:
```bash
./deploy-vps.sh
```

## 📱 URLs após deploy

- **Frontend**: `http://SEU_IP:3003`
- **API**: `http://SEU_IP:8002` 
- **Docs**: `http://SEU_IP:8002/docs`

## 🛠️ Comandos úteis

```bash
# Ver logs
docker-compose logs -f

# Ver status
docker-compose ps

# Parar tudo
docker-compose down

# Reiniciar serviço específico
docker-compose restart api

# Atualizar código e redeploy
git pull && ./deploy-vps.sh
```

## 🔥 Workers de Alta Performance

O projeto inclui workers extras para alta demanda:

```bash
# Worker adicional (30-50 jobs)
docker-compose --profile high-load up -d

# Worker ultra (50-100+ jobs) 
docker-compose --profile ultra-high-load up -d
```

## 🚨 Troubleshooting

Se der erro, verificar:
1. **Portas liberadas**: `sudo ufw allow 3003 && sudo ufw allow 8002`
2. **Logs**: `docker-compose logs -f`
3. **Espaço em disco**: `df -h`
4. **Memória**: `free -h`