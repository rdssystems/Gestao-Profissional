#!/bin/bash
# Restaura o banco de dados de produção no ambiente de desenvolvimento local.
# Uso: bash dev_restore_db.sh

set -e

DUMP="dev_restore.dump"
CONTAINER="gq-db"

if [ ! -f "$DUMP" ]; then
    echo "Arquivo $DUMP não encontrado."
    echo "Baixe o dump da VPS primeiro ou execute: python dev_pull_db.py"
    exit 1
fi

echo ">>> Aguardando o banco estar pronto..."
until docker exec "$CONTAINER" pg_isready -U gestao_user -q; do
    sleep 1
done

echo ">>> Recriando banco limpo..."
docker exec "$CONTAINER" psql -U gestao_user -c "DROP DATABASE IF EXISTS gestao_db;" postgres
docker exec "$CONTAINER" psql -U gestao_user -c "CREATE DATABASE gestao_db;" postgres

echo ">>> Restaurando dump..."
docker cp "$DUMP" "$CONTAINER":/tmp/restore.dump
docker exec "$CONTAINER" pg_restore -U gestao_user -d gestao_db /tmp/restore.dump || true
docker exec "$CONTAINER" rm /tmp/restore.dump

echo ">>> Banco restaurado com sucesso!"
