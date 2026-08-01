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

# Guarda de seguranca: o container "gq-db" tem o MESMO NOME em dev e em
# producao (docker-compose.yml). Sem checar isto, apontar DOCKER_HOST (ou
# copiar/colar este script) para o Docker da VPS por engano derruba o banco
# de producao com um DROP DATABASE sem confirmacao nenhuma.
if [ -n "$DOCKER_HOST" ]; then
    echo "ERRO: DOCKER_HOST está definido ($DOCKER_HOST) — este script só deve"
    echo "rodar contra o Docker LOCAL de desenvolvimento. Aborting."
    exit 1
fi

if ! docker inspect "$CONTAINER" --format '{{ range .Mounts }}{{ .Name }} {{ end }}' 2>/dev/null | grep -q 'postgres_data_dev'; then
    echo "ERRO: o container '$CONTAINER' não parece usar o volume de dev"
    echo "(postgres_data_dev). Isto pode ser o banco de PRODUÇÃO. Abortando"
    echo "por segurança — confira 'docker inspect $CONTAINER' antes de rodar."
    exit 1
fi

read -p ">>> Isso vai APAGAR o banco 'gestao_db' deste container e restaurar o dump. Confirma? (digite 'sim'): " CONFIRMA
if [ "$CONFIRMA" != "sim" ]; then
    echo "Cancelado."
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
