import os
import sys
import django

# Adicionar a pasta raiz ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from escolas.models import Escola

print("--- Classificando Escolas ---")
escolas = Escola.objects.all()
for e in escolas:
    old_tipo = e.tipo
    if 'uditech' in e.nome.lower():
        e.tipo = 'UDITECH'
    else:
        e.tipo = 'CP'
    e.save()
    print(f"Escola: {e.nome} | Tipo Anterior: {old_tipo} -> Tipo Novo: {e.tipo}")

print("--- Concluído ---")
