#!/bin/bash

# Configurações do Backup
DB_CONTAINER="gq-db"
DB_NAME="gestao_db"
DB_USER="gestao_user"
BACKUP_DIR="/app/backups" # Caminho dentro/fora do container conforme necessário
DATE=$(date +%Y-%m-%d_%H-%M-%S)
FILE_NAME="backup_${DB_NAME}_${DATE}.sql.gz"
REMOTE_NAME="gdrive" # Nome que você deu na configuração do rclone
REMOTE_PATH="ZimaOS_Backups" # Pasta no Google Drive

# Garante que a pasta de logs/backups existe localmente
mkdir -p "$BACKUP_DIR"

echo "Iniciando backup do banco de dados: $DB_NAME..."

DB_PASS="gestao_pass"

# 1. Realiza o dump do PostgreSQL e compacta
docker exec -e PGPASSWORD="$DB_PASS" $DB_CONTAINER pg_dump -U $DB_USER $DB_NAME | gzip > "$BACKUP_DIR/$FILE_NAME"

if [ $? -eq 0 ]; then
    echo "Dump concluído com sucesso: $FILE_NAME"
    
    # 2. Envia para o Google Drive via rclone
    echo "Enviando para o Google Drive..."
    rclone copy "$BACKUP_DIR/$FILE_NAME" "${REMOTE_NAME}:${REMOTE_PATH}"
    
    if [ $? -eq 0 ]; then
        echo "Backup enviado com sucesso para o Google Drive!"
        
        # 3. Limpeza (opcional): remove backups locais com mais de 7 dias
        find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +7 -delete
    else
        echo "ERRO ao enviar para o Google Drive. Verifique a configuração do rclone."
    fi
else
    echo "ERRO ao realizar o dump do banco de dados."
fi
