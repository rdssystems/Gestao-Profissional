#!/bin/bash
# ────────────────────────────────────────────────────────────
# Backup sob demanda do banco de dados.
# Faz o dump do PostgreSQL e envia para:
#   1) Google Cloud Storage (via backup_upload.py, dentro do container)
#   2) Google Drive montado em /media/.../Gestao-Profissional/backups/manual
# Mantém apenas os 10 backups manuais mais recentes no Drive.
#
# Uso:  sudo bash backup_agora.sh
# ────────────────────────────────────────────────────────────
set -u

DATE=$(date +%Y%m%d_%H%M%S)
FILE="manual_${DATE}.dump"
TEMP="/tmp/${FILE}"
GDRIVE="/media/qualificacaoudia_google_drive_1777986114/Gestao-Profissional/backups/manual"
KEEP=10

echo "--- Backup sob demanda iniciado ($DATE) ---"

# 1. Dump do banco
echo ">>> [1/4] Gerando dump do banco..."
if ! docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > "$TEMP"; then
    echo "!!! ERRO ao gerar o dump. Abortando."
    rm -f "$TEMP"
    exit 1
fi
if [ ! -s "$TEMP" ]; then
    echo "!!! ERRO: dump vazio (0 bytes). Abortando."
    rm -f "$TEMP"
    exit 1
fi
echo "    Dump gerado: $TEMP ($(du -h "$TEMP" | cut -f1))"

# 2. Upload para o Google Cloud Storage
echo ">>> [2/4] Enviando para o Google Cloud Storage..."
if docker cp "$TEMP" "gq-app:/tmp/${FILE}" && docker exec gq-app python /app/backup_upload.py "$FILE"; then
    echo "    GCS OK"
else
    echo "!!! AVISO: falha no upload para o GCS. Continuando para o Google Drive."
fi

# 3. Copiar para o Google Drive montado
echo ">>> [3/4] Salvando no Google Drive..."
if mkdir -p "$GDRIVE" && cp "$TEMP" "$GDRIVE/$FILE"; then
    echo "    Salvo em: $GDRIVE/$FILE"
else
    echo "!!! ERRO ao salvar no Google Drive (o drive está montado?). Abortando."
    rm -f "$TEMP"
    exit 1
fi

# 4. Retenção: manter apenas os $KEEP mais recentes
TOTAL=$(ls -1 "$GDRIVE"/*.dump 2>/dev/null | wc -l)
if [ "$TOTAL" -gt "$KEEP" ]; then
    TO_DELETE=$((TOTAL - KEEP))
    echo "    Removendo $TO_DELETE backup(s) antigo(s) (mantendo $KEEP)..."
    ls -1t "$GDRIVE"/*.dump | tail -n "$TO_DELETE" | while read -r f; do
        rm -f "$f"
    done
fi
echo "    Backups manuais no Drive: $(ls -1 "$GDRIVE"/*.dump 2>/dev/null | wc -l)"

# Limpeza do temporário local
rm -f "$TEMP"
echo "--- Backup concluído com sucesso: GCS + Google Drive ($FILE) ---"
