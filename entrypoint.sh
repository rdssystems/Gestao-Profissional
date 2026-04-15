#!/bin/sh

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ "$DEBUG" = "True" ]; then
    echo "Starting in DEBUG environment (auto reload enabled)..."
    exec python manage.py runserver 0.0.0.0:8000
else
    echo "Starting in PRODUCTION environment (Daphne enabled)..."
    exec daphne -b 0.0.0.0 -p 8000 gestao_qualificacao_profissional.asgi:application
fi
