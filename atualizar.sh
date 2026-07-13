#!/bin/bash

echo "--- Iniciando Atualizacao do Sistema ---"

# ──────────────────────────────────────────────────
# 0. BACKUP PRE-UPDATE (GCS + Google Drive)
# ──────────────────────────────────────────────────
read -p ">>> Deseja fazer backup antes de atualizar? (s/N): " FAZER_BACKUP

if [[ "$FAZER_BACKUP" =~ ^[sS]$ ]]; then
    echo ">>> [PRE-UPDATE] Gerando backup do banco..."
    BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="pre_update_${BACKUP_DATE}.dump"
    TEMP="/tmp/${BACKUP_FILE}"
    GDRIVE="/media/qualificacaoudia_google_drive_1777986114/Gestao-Profissional/backups/pre_update"

    # Dump
    sudo docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > "$TEMP"

    # Enviar para GCS
    sudo docker cp "$TEMP" "gq-app:/tmp/${BACKUP_FILE}"
    sudo docker exec gq-app python /app/backup_upload.py "$BACKUP_FILE"

    # Salvar no Google Drive
    mkdir -p "$GDRIVE"
    cp "$TEMP" "$GDRIVE/$BACKUP_FILE"

    # Manter apenas os 10 mais recentes no Drive
    TOTAL=$(ls -1 "$GDRIVE"/*.dump 2>/dev/null | wc -l)
    if [ "$TOTAL" -gt 10 ]; then
        TO_DELETE=$((TOTAL - 10))
        ls -1t "$GDRIVE"/*.dump | tail -n "$TO_DELETE" | while read f; do
            rm -f "$f"
        done
    fi

    rm -f "$TEMP"
    echo ">>> [PRE-UPDATE] Backup salvo: GCS + Google Drive ($BACKUP_FILE)"
else
    echo ">>> Backup pulado."
fi

# ──────────────────────────────────────────────────
# 1. Git pull
# ──────────────────────────────────────────────────
echo ">>> Puxando mudancas do Git..."
git fetch origin main
git reset --hard origin/main
git clean -fd

# ──────────────────────────────────────────────────
# 2. Rebuild containers
# ──────────────────────────────────────────────────
echo ">>> Reconstruindo containers..."
export DOCKER_CONFIG=/tmp/.docker
sudo -E docker compose up -d --build

# ──────────────────────────────────────────────────
# 3. Migrations
# ──────────────────────────────────────────────────
echo ">>> Verificando migrations..."
sudo docker exec gq-app python manage.py makemigrations
echo ">>> Aplicando migrations..."
sudo docker exec gq-app python manage.py migrate

# ──────────────────────────────────────────────────
# 4. Static files
# ──────────────────────────────────────────────────
echo ">>> Coletando arquivos estaticos..."
sudo docker exec gq-app python manage.py collectstatic --no-input

# ──────────────────────────────────────────────────
# 5. Limpeza
# ──────────────────────────────────────────────────
echo ">>> Limpando imagens antigas..."
sudo docker image prune -f

echo "--- Atualizacao concluida com sucesso! ---"
