#!/bin/bash
set -e

DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="gestao_db_${DATE}.dump"
TEMP_FILE="/tmp/${FILENAME}"
APP_DIR="/DATA/AppData/Gestao-Profissional"
GDRIVE="/media/qualificacaoudia_google_drive_1777986114/Gestao-Profissional/backups/diario"
LOG="$APP_DIR/backup_gcs.log"

# So le a linha do webhook, nao o .env inteiro (evita rodar conteudo
# arbitrario de um arquivo que tambem guarda outros segredos).
DISCORD_WEBHOOK_URL=""
if [ -f "$APP_DIR/.env" ]; then
    DISCORD_WEBHOOK_URL=$(grep -m1 '^DISCORD_WEBHOOK_URL=' "$APP_DIR/.env" | cut -d '=' -f2-)
fi

notificar_discord() {
    # $1=titulo  $2=descricao (\n vira quebra de linha)  $3=cor decimal
    [ -z "$DISCORD_WEBHOOK_URL" ] && return 0
    curl -s -H "Content-Type: application/json" \
        -d "{\"embeds\":[{\"title\":\"$1\",\"description\":\"$2\",\"color\":$3}]}" \
        "$DISCORD_WEBHOOK_URL" >> "$LOG" 2>&1
}

alertar_falha_total() {
    # So dispara e-mail quando os DOIS destinos falham no mesmo ciclo —
    # uma falha isolada ainda tem o outro destino como redundancia.
    echo "    ALERTA: Drive e GCS falharam no mesmo ciclo. Enviando e-mail..." >> "$LOG"
    docker exec gq-app python manage.py alertar_falha_backup "$1" >> "$LOG" 2>&1
}

echo "======================================" >> "$LOG"
echo "  BACKUP DIARIO INICIADO: $DATE"       >> "$LOG"
echo "======================================" >> "$LOG"

# 1. Dump
echo ">>> [1/5] Gerando dump..."             >> "$LOG"
docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > "$TEMP_FILE"

# Aborta se o dump saiu vazio/zerado (pg_dump pode sair com status 0 mesmo
# assim, ex.: disco cheio no meio da escrita) — sem isso o backup diario
# "concluia com sucesso" e sobrescrevia o Drive/GCS com um arquivo inutil.
DUMP_SIZE=$(stat -c%s "$TEMP_FILE" 2>/dev/null || stat -f%z "$TEMP_FILE")
if [ -z "$DUMP_SIZE" ] || [ "$DUMP_SIZE" -eq 0 ]; then
    echo "    ERRO: dump ficou vazio (0 bytes). Abortando backup." >> "$LOG"
    rm -f "$TEMP_FILE"
    alertar_falha_total "O dump do banco saiu vazio (0 bytes) — nenhum backup foi gerado, nem para o Drive nem para o GCS."
    notificar_discord "❌ Backup Gestão Profissional FALHOU - $DATE" "🗄️ Dump do banco saiu vazio (0 bytes). Nenhum arquivo foi gerado." 15158332
    exit 1
fi
echo "    Dump: $TEMP_FILE ($DUMP_SIZE bytes)" >> "$LOG"

# 2. Salvar no Google Drive primeiro (independe do GCS — se o GCS falhar,
# o backup local no Drive nao pode ficar refem disso). Nao fatal: uma falha
# aqui fica registrada, mas o script continua para tentar o GCS.
DRIVE_OK=0
echo ">>> [2/5] Salvando no Google Drive..." >> "$LOG"
if mkdir -p "$GDRIVE" >> "$LOG" 2>&1 && cp "$TEMP_FILE" "$GDRIVE/$FILENAME" >> "$LOG" 2>&1; then
    DRIVE_OK=1
    echo "    Salvo: $GDRIVE/$FILENAME"      >> "$LOG"

    # Manter apenas os 10 mais recentes no Drive
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
else
    echo "    AVISO: falha ao salvar no Google Drive (mount indisponivel?)" >> "$LOG"
fi

# 3. Upload GCS — tambem nao fatal: uma falha aqui (ex.: permissao IAM
# revogada, billing desativado) fica registrada, mas nao derruba o script.
GCS_OK=0
echo ">>> [3/5] Enviando para GCS..."        >> "$LOG"
if docker cp "$TEMP_FILE" "gq-app:/tmp/${FILENAME}" >> "$LOG" 2>&1 \
    && docker exec gq-app python /app/backup_upload.py "$FILENAME" >> "$LOG" 2>&1; then
    GCS_OK=1
    echo "    GCS OK"                        >> "$LOG"
else
    echo "    AVISO: upload para o GCS falhou" >> "$LOG"
fi

# 4. Se os DOIS destinos falharam neste ciclo, alertar por e-mail
if [ "$DRIVE_OK" -eq 0 ] && [ "$GCS_OK" -eq 0 ]; then
    alertar_falha_total "Nem o Google Drive nem o GCS aceitaram o backup de $DATE. Veja o log completo para os erros de cada etapa."
fi

# 4b. Discord: uma mensagem por rodada (3x/dia), sempre — verde se os dois
# destinos ok, laranja se so um, vermelho se nenhum.
DRIVE_TXT=$([ "$DRIVE_OK" -eq 1 ] && echo "✅ OK" || echo "❌ FALHOU")
GCS_TXT=$([ "$GCS_OK" -eq 1 ] && echo "✅ OK" || echo "❌ FALHOU")
if [ "$DRIVE_OK" -eq 1 ] && [ "$GCS_OK" -eq 1 ]; then
    notificar_discord "✅ Backup Gestão Profissional OK - $DATE" "💾 Google Drive: $DRIVE_TXT\n☁️ Google Cloud Storage: $GCS_TXT" 3066993
elif [ "$DRIVE_OK" -eq 1 ] || [ "$GCS_OK" -eq 1 ]; then
    notificar_discord "⚠️ Backup Gestão Profissional com falha parcial - $DATE" "💾 Google Drive: $DRIVE_TXT\n☁️ Google Cloud Storage: $GCS_TXT" 15105570
else
    notificar_discord "❌ Backup Gestão Profissional FALHOU TOTALMENTE - $DATE" "💾 Google Drive: $DRIVE_TXT\n☁️ Google Cloud Storage: $GCS_TXT" 15158332
fi

# 5. Limpar temp
echo ">>> [5/5] Limpando temporarios..."     >> "$LOG"
rm -f "$TEMP_FILE"

echo "  BACKUP DIARIO CONCLUIDO: $(date +"%Y-%m-%d %H:%M:%S")" >> "$LOG"
echo ""                                      >> "$LOG"
