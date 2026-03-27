import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from cursos.models import Curso

print("Verificando duplicatas de token_acesso...")
all_cursos = Curso.objects.all()
tokens_seen = set()
duplicates_fixed = 0

for c in all_cursos:
    if c.token_acesso is None or c.token_acesso == "" or c.token_acesso in tokens_seen:
        new_token = uuid.uuid4()
        while Curso.objects.filter(token_acesso=new_token).exists():
            new_token = uuid.uuid4()
        c.token_acesso = new_token
        c.save()
        duplicates_fixed += 1
    tokens_seen.add(c.token_acesso)

print(f"Total de cursos processados: {all_cursos.count()}")
print(f"Total de duplicatas/nulos corrigidos: {duplicates_fixed}")
