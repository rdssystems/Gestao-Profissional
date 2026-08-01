#!/bin/bash
# Roda a cada 3 dias via cron. Envia um e-mail de status (tudo certo OU
# problema) do backup diario, independente de ter falhado ou nao — e um
# "ainda estou vivo", nao so um alerta de falha.
APP_DIR="/DATA/AppData/Gestao-Profissional"
GDRIVE="/media/qualificacaoudia_google_drive_1777986114/Gestao-Profissional/backups/diario"
LOG="$APP_DIR/verificar_saude_backup.log"
IDADE_MAXIMA_HORAS=30

echo "======================================" >> "$LOG"
echo "  CHECAGEM DE SAUDE: $(date +%Y%m%d_%H%M%S)" >> "$LOG"
echo "======================================" >> "$LOG"

DRIVE_LATEST=$(ls -t "$GDRIVE"/*.dump 2>/dev/null | head -1)
if [ -z "$DRIVE_LATEST" ]; then
    DRIVE_STATUS="falha"
    DRIVE_DETALHE="Nenhum backup encontrado na pasta do Drive"
else
    AGORA_EPOCH=$(date +%s)
    ARQUIVO_EPOCH=$(stat -c%Y "$DRIVE_LATEST" 2>/dev/null || stat -f%m "$DRIVE_LATEST")
    IDADE_HORAS=$(( (AGORA_EPOCH - ARQUIVO_EPOCH) / 3600 ))
    if [ "$IDADE_HORAS" -gt "$IDADE_MAXIMA_HORAS" ]; then
        DRIVE_STATUS="falha"
        DRIVE_DETALHE="Ultimo backup ha ${IDADE_HORAS}h (esperado < ${IDADE_MAXIMA_HORAS}h) - $(basename "$DRIVE_LATEST")"
    else
        DRIVE_STATUS="ok"
        DRIVE_DETALHE="ultimo backup ha ${IDADE_HORAS}h - $(basename "$DRIVE_LATEST")"
    fi
fi

echo "    Drive: $DRIVE_STATUS ($DRIVE_DETALHE)" >> "$LOG"

docker exec gq-app python manage.py enviar_status_backup "$DRIVE_STATUS" "$DRIVE_DETALHE" >> "$LOG" 2>&1

echo "  CHECAGEM CONCLUIDA: $(date +"%Y-%m-%d %H:%M:%S")" >> "$LOG"
echo "" >> "$LOG"
