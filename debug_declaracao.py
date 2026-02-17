import os
import django
import sys
from datetime import date

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from alunos.models import Aluno
from cursos.models import Inscricao
from declaracao.utils import get_aluno_status_para_inscricao

def debug_cpf_search(cpf_input, user_school_id=None):
    print(f"--- Debugging CPF: {cpf_input} (School ID: {user_school_id}) ---")
    
    cpf_digits = ''.join(filter(str.isdigit, cpf_input))
    
    alunos = Aluno.objects.filter(cpf=cpf_digits)
    if user_school_id:
        alunos = alunos.filter(escola_id=user_school_id)
        
    print(f"Found {alunos.count()} Aluno records.")
    
    for aluno in alunos:
        print(f"Aluno: {aluno.nome_completo} (ID: {aluno.id}, Escola: {aluno.escola})")
        
        inscricoes = Inscricao.objects.filter(aluno=aluno).select_related('curso')
        if user_school_id:
             inscricoes = inscricoes.filter(curso__escola_id=user_school_id)
             
        print(f"  Found {inscricoes.count()} Inscricao records.")
        
        for inscricao in inscricoes:
            status = get_aluno_status_para_inscricao(inscricao)
            print(f"    Curso: {inscricao.curso.nome}")
            print(f"      Dates: {inscricao.curso.data_inicio} to {inscricao.curso.data_fim}")
            print(f"      Inscricao Status: {inscricao.status}")
            print(f"      Calculated Status: {status}")
            
            if status in ['matriculado', 'cursando', 'concluido']:
                print("      -> ACTION: ENABLED")
            else:
                print("      -> ACTION: DISABLED (Visible but not actionable)")

if __name__ == "__main__":
    # Try to find a student to test
    first_aluno = Aluno.objects.first()
    if first_aluno:
        # Simulate searching for this student within their own school
        debug_cpf_search(first_aluno.cpf, first_aluno.escola_id)
    else:
        print("No students in database.")
