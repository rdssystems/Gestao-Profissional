#!/bin/sh
# Aguarda o banco de dados ficar pronto (se estiver usando Postgres)
if [ "$DB_ENGINE" = "django.db.backends.postgresql" ]; then
    echo "Aguardando o PostgreSQL em $DB_HOST:$DB_PORT..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL pronto!"
fi

# Aplica migrações
echo "Aplicando migrações..."
python manage.py migrate --noinput

# Coleta arquivos estáticos
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# Inicia o servidor com Daphne (suporte a Websockets/Channels)
echo "Iniciando servidor Daphne..."
exec daphne -b 0.0.0.0 -p 8000 gestao_qualificacao_profissional.asgi:application
