import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from django.contrib.auth import authenticate
from usuarios.forms import CustomAuthenticationForm

username = 'klismanrds'
password = '32166096'

print(f"--- Diagnóstico de Login para '{username}' ---")

# 1. Testar se o usuário existe
from django.contrib.auth.models import User
u = User.objects.filter(username=username).first()
if u:
    print(f"Usuário encontrado! Ativo: {u.is_active}, Staff: {u.is_staff}, Superuser: {u.is_superuser}")
else:
    print("ERRO: Usuário não encontrado no banco de dados.")

# 2. Testar autenticação direta
user = authenticate(username=username, password=password)
if user:
    print("Autenticação DIRETA (authenticate()): SUCESSO")
else:
    print("Autenticação DIRETA (authenticate()): FALHOU")

# 3. Testar via formulário CustomAuthenticationForm
form = CustomAuthenticationForm(data={'username': username, 'password': password})
if form.is_valid():
    print("Validação via CustomAuthenticationForm: SUCESSO")
else:
    print("Validação via CustomAuthenticationForm: FALHOU")
    print(f"Erros do formulário: {form.errors.as_text()}")
