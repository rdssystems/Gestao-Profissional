#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="gestao_db_${DATE}.dump"
TEMP_FILE="/tmp/${FILENAME}"
APP_DIR="/DATA/AppData/Gestao-Profissional"
GDRIVE="/media/qualificacaoudia_google_drive_1777986114/Gestao-Profissional/backups/diario"
LOG="$APP_DIR/backup_gcs.log"

echo "======================================" >> "$LOG"
echo "  BACKUP DIARIO INICIADO: $DATE"       >> "$LOG"
echo "======================================" >> "$LOG"

# 1. Dump
echo ">>> [1/5] Gerando dump..."             >> "$LOG"
docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > "$TEMP_FILE"
echo "    Dump: $TEMP_FILE"                  >> "$LOG"

# 2. Upload GCS
echo ">>> [2/5] Copiando para gq-app..."     >> "$LOG"
docker cp "$TEMP_FILE" "gq-app:/tmp/${FILENAME}"
echo ">>> [3/5] Enviando para GCS..."        >> "$LOG"
docker exec gq-app python /app/backup_upload.py "$FILENAME"

# 3. Salvar no Google Drive
echo ">>> [4/5] Salvando no Google Drive..." >> "$LOG"
mkdir -p "$GDRIVE"
cp "$TEMP_FILE" "$GDRIVE/$FILENAME"
echo "    Salvo: $GDRIVE/$FILENAME"          >> "$LOG"

# 4. Manter apenas os 10 mais recentes no Drive
TOTAL=$(ls -1 "$GDRIVE"/*.dump 2>/dev/null | wc -l)
if [ "$TOTAL" -gt 10 ]; then
    TO_DELETE=$((TOTAL - 10))
    echo "    Removendo $TO_DELETE backup(s) antigo(s)..." >> "$LOG"
    ls -1t "$GDRIVE"/*.dump | tail -n "$TO_DELETE" | while read f; do
        rm -f "$f"
        echo "    Removido: $f" >> "$LOG"
    done
fi
echo "    Backups no Drive: $(ls -1 "$GDRIVE"/*.dump 2>/dev/null | wc -l)" >> "$LOG"

# 5. Limpar temp
echo ">>> [5/5] Limpando temporarios..."     >> "$LOG"
rm -f "$TEMP_FILE"

echo "  BACKUP DIARIO CONCLUIDO: $(date +"%Y-%m-%d %H:%M:%S")" >> "$LOG"
echo ""                                      >> "$LOG"
