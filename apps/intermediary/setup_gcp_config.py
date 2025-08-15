#!/usr/bin/env python3
"""
Script para configurar automaticamente as variáveis GCS baseadas nas credenciais GCP
"""
import json
import os
from pathlib import Path

def load_gcp_credentials():
    """Carrega as credenciais GCP e retorna o project_id"""
    cred_file = Path(__file__).parent / "gcp-credentials.json"
    
    if not cred_file.exists():
        # Fallback para o arquivo example
        cred_file = Path(__file__).parent / "gcp-credentials.example.json"
    
    if not cred_file.exists():
        raise FileNotFoundError("Arquivo de credenciais GCP não encontrado")
    
    with open(cred_file, 'r') as f:
        credentials = json.load(f)
    
    return credentials

def update_env_file():
    """Atualiza o arquivo .env com as configurações corretas do GCP"""
    credentials = load_gcp_credentials()
    project_id = credentials.get('project_id')
    
    if not project_id:
        raise ValueError("project_id não encontrado nas credenciais")
    
    # Configurações GCS baseadas no projeto
    gcs_bucket = project_id  # Usar o mesmo nome do projeto como bucket
    
    env_file = Path(__file__).parent / ".env"
    
    # Ler arquivo .env atual
    env_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Atualizar/adicionar configurações GCS
    updated_lines = []
    gcs_bucket_updated = False
    
    for line in env_lines:
        if line.startswith('GCS_BUCKET='):
            updated_lines.append(f'GCS_BUCKET={gcs_bucket}\n')
            gcs_bucket_updated = True
        else:
            updated_lines.append(line)
    
    # Adicionar configuração se não existir
    if not gcs_bucket_updated:
        updated_lines.append(f'GCS_BUCKET={gcs_bucket}\n')
    
    # Escrever arquivo atualizado
    with open(env_file, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"✅ Configuração GCS atualizada:")
    print(f"   Project ID: {project_id}")
    print(f"   GCS Bucket: {gcs_bucket}")
    print(f"   Arquivo: {env_file}")

if __name__ == "__main__":
    try:
        update_env_file()
    except Exception as e:
        print(f"❌ Erro: {e}")
        exit(1)