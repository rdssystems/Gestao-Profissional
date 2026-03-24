import os
import django
import random
import string
from datetime import date, timedelta

# Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from alunos.models import Aluno
from escolas.models import Escola

def generate_cpf():
    return "".join([str(random.randint(0, 9)) for _ in range(11)])

def create_dummy_students(school_name, count=10):
    try:
        escola = Escola.objects.get(nome__icontains=school_name)
    except Escola.DoesNotExist:
        print(f"Escola '{school_name}' não encontrada.")
        return
    except Escola.MultipleObjectsReturned:
        escola = Escola.objects.filter(nome__icontains=school_name).first()
        print(f"Múltiplas escolas encontradas, usando: {escola.nome}")

    first_names = ["João", "Maria", "Pedro", "Ana", "Lucas", "Julia", "Carlos", "Fernanda", "Gabriel", "Camila"]
    last_names = ["Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Almeida", "Pereira", "Carvalho", "Gomes"]

    created_count = 0
    for i in range(count):
        nome = f"{random.choice(first_names)} {random.choice(last_names)} {random.choice(last_names)}"
        cpf = generate_cpf()
        
        # Garante CPF único (tentando até 5 vezes)
        for _ in range(5):
            if not Aluno.objects.filter(cpf=cpf).exists():
                break
            cpf = generate_cpf()

        data_nasc = date(1980, 1, 1) + timedelta(days=random.randint(0, 15000))
        
        try:
            Aluno.objects.create(
                escola=escola,
                nome_completo=nome,
                cpf=cpf,
                data_nascimento=data_nasc,
                email=f"aluno{i+random.randint(100,999)}@exemplo.com",
                whatsapp=f"3499{random.randint(1000000, 9999999)}",
                logradouro="Rua Fictícia",
                numero=str(random.randint(1, 1000)),
                bairro="Bairro Planejado",
                cidade="Uberlândia",
                estado="MG"
            )
            created_count += 1
        except Exception as e:
            print(f"Erro ao criar aluno {i}: {e}")

    print(f"Sucesso: {created_count} alunos criados para {escola.nome}.")

if __name__ == "__main__":
    create_dummy_students("CP Luizote Civil", 10)
