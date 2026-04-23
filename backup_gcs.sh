#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="gestao_db_${DATE}.dump"
TEMP_FILE="/tmp/${FILENAME}"

echo "======================================"
echo "  BACKUP INICIADO: $DATE"
echo "======================================"

# 1. Gerar dump diretamente do container do banco (pg_dump 18 nativo)
echo ">>> [1/4] Gerando dump do PostgreSQL via gq-db..."
sudo docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > "$TEMP_FILE"
echo "    Dump gerado: $TEMP_FILE"

# 2. Copiar o dump para dentro do container do Django
echo ">>> [2/4] Copiando dump para o container gq-app..."
sudo docker cp "$TEMP_FILE" "gq-app:/tmp/${FILENAME}"

# 3. Rodar o script de upload dentro do container do Django (que já tem google-cloud-storage)
echo ">>> [3/4] Enviando para o Google Cloud Storage..."
sudo docker exec gq-app python /app/backup_upload.py "$FILENAME"

# 4. Limpar arquivo temporário da VPS
echo ">>> [4/4] Limpando arquivos temporários..."
rm -f "$TEMP_FILE"

echo "======================================"
echo "  BACKUP CONCLUÍDO COM SUCESSO!"
echo "======================================"
