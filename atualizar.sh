#!/bin/bash

echo "--- Iniciando Atualização do Sistema ---"

# 1. Baixar as últimas mudanças do GitHub
echo ">>> Puxando mudanças do Git..."
git pull origin main

# 2. Reconstruir e subir os containers (com fix para ZimaOS Read-Only)
echo ">>> Reconstruindo containers (Docker Build)..."
export DOCKER_CONFIG=/tmp/.docker
sudo -E docker compose up -d --build

# 3. Rodar as migrações do Django
echo ">>> Verificando migrações (makemigrations)..."
sudo docker exec gq-app python manage.py makemigrations

echo ">>> Aplicando migrações (migrate)..."
sudo docker exec gq-app python manage.py migrate

# 4. Coletar arquivos estáticos
echo ">>> Coletando arquivos estáticos (collectstatic)..."
sudo docker exec gq-app python manage.py collectstatic --no-input

# 5. Limpeza de imagens antigas
echo ">>> Limpando imagens antigas..."
sudo docker image prune -f

echo "--- Atualização concluída com sucesso! ---"
