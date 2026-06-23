import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from escolas.models import Escola
from cursos.models import Curso
from alunos.models import Aluno

print("=== ESCOLAS E SEUS DADOS ===")
for escola in Escola.objects.all():
    aluno_count = Aluno.objects.filter(escola=escola).count()
    curso_count = Curso.objects.filter(escola=escola).count()
    print(f"ID: {escola.id} | Nome: {escola.nome} | Tipo: {escola.tipo} | Alunos: {aluno_count} | Cursos: {curso_count}")
