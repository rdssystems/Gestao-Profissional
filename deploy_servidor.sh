#!/bin/bash

# Script de Deploy Automatizado para o Servidor
# Este script deve ser executado no servidor Linux para atualizar o sistema

echo "🚀 Iniciando atualização do sistema..."

# 1. Entrar no diretório do projeto (ajuste o caminho se necessário)
# cd /caminho/para/o/projeto/gestao-qualificacao

# 2. Puxar as alterações do GitHub
echo "📥 Puxando alterações do GitHub..."
git pull origin main

# 3. Ativar o ambiente virtual (ajuste o caminho se necessário)
# source venv/bin/activate

# 4. Instalar dependências atualizadas
echo "📦 Atualizando dependências..."
pip install -r requirements.txt

# 5. Aplicar migrações do banco de dados
echo "🗄️ Aplicando migrações (Banco de Dados)..."
python manage.py migrate --noinput

# 6. Coletar arquivos estáticos
echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

# 7. Reiniciar o serviço do servidor (Gunicorn/UWSGI/etc)
echo "🔄 Reiniciando o serviço..."
# sudo systemctl restart gestao_qualificacao

echo "✅ Sistema atualizado com sucesso!"
