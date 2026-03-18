import os
import django
import sqlite3
import re
import sys
from datetime import datetime
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from alunos.models import Aluno
from escolas.models import Escola

def clean_numeric(val):
    if not val: return ""
    return re.sub(r'\D', '', str(val))

def format_date(val):
    if not val or str(val).lower() == 'nan' or str(val).strip() == '':
        return None
    val = str(val).split(' ')[0] # Pegar apenas a parte da data se tiver hora
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d%m%Y'):
        try:
            return datetime.strptime(val, fmt).date()
        except:
            continue
    return None

def map_choice(val, choices, default=None):
    if not val: return default
    val = str(val).strip().lower()
    for key, label in choices:
        if val in label.lower() or label.lower() in val:
            return key
    return default

def migrate(school_name, db_path):
    # Validar arquivo
    if not os.path.exists(db_path):
        print(f"Erro: Arquivo '{db_path}' não encontrado.")
        return

    # Escola Alvo
    try:
        escola = Escola.objects.get(nome__icontains=school_name)
    except Escola.DoesNotExist:
        print(f"Erro: Escola '{school_name}' não encontrada no banco de dados.")
        return
    except Escola.MultipleObjectsReturned:
        escola = Escola.objects.filter(nome__icontains=school_name).first()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Verificar se a tabela 'dados' existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dados'")
    if not cursor.fetchone():
        print(f"Erro: Tabela 'dados' não encontrada no arquivo {db_path}")
        conn.close()
        return

    cursor.execute("SELECT * FROM dados")
    rows = cursor.fetchall()
    
    total = len(rows)
    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    print(f"Iniciando migração de {total} registros para {escola.nome} usando {db_path}...")

    # CPF cache para evitar duplicados no próprio arquivo dirty
    cpfs_processados = set()

    for row in rows:
        try:
            raw_cpf = clean_numeric(row['Cpf'])
            if not raw_cpf or len(raw_cpf) != 11:
                # Tenta corrigir se faltar zero à esquerda
                if len(raw_cpf) == 10:
                    raw_cpf = "0" + raw_cpf
                else:
                    # Se tiver menos que 10 ou mais que 11, ainda tentamos tratar ou pulamos
                    if len(raw_cpf) < 10 and len(raw_cpf) > 0:
                         raw_cpf = raw_cpf.zfill(11)
                    else:
                        print(f"CPF Inválido: {row['Cpf']} ({row['Nome']}) - Pulando.")
                        skipped += 1
                        continue

            if raw_cpf in cpfs_processados:
                skipped += 1
                continue
            
            cpfs_processados.add(raw_cpf)

            # Preparar dados
            aluno_data = {
                'escola': escola,
                'nome_completo': str(row['Nome']).strip().upper() if row['Nome'] else "SEM NOME",
                'cpf': raw_cpf,
                'rg': row['Rg'] if row['Rg'] else None,
                'orgao_exp': row['OrgaoEmissor'] if row['OrgaoEmissor'] else None,
                'data_emissao': format_date(row['DataEmissao']),
                'data_nascimento': format_date(row['datanasc']),
                'sexo': 'M' if 'masc' in str(row['Sexo']).lower() else 'F',
                'estado_civil': map_choice(row['Estadocivil'], Aluno.ESTADO_CIVIL_CHOICES, 'Solteiro'),
                'cor_raca': map_choice(row['Cor'], Aluno.COR_RACA_CHOICES, 'Parda'),
                'nome_mae': row['Filiacao'] if row['Filiacao'] else "NÃO INFORMADO",
                'naturalidade': row['Naturalidade'] if row['Naturalidade'] else "NÃO INFORMADO",
                'uf_naturalidade': row['Uf'][:2].upper() if row['Uf'] else 'MG',
                'deficiencia': True if str(row['Deficiencia']).lower() in ('sim', 's', '1') else False,
                'escolaridade': map_choice(row['Escolaridade'], Aluno.ESCOLARIDADE_CHOICES, 'Fundamental Completo'),
                'email_principal': str(row['email']).strip().lower() if row['email'] else "sem@email.com",
                'telefone_principal': clean_numeric(row['Telefone1'])[:11] if row['Telefone1'] else "00000000000",
                'whatsapp': clean_numeric(row['Telefone2'])[:11] if row['Telefone2'] else (clean_numeric(row['Telefone1'])[:11] if row['Telefone1'] else "00000000000"),
                'endereco_cep': clean_numeric(row['Cep'])[:9] if row['Cep'] else "38400000",
                'endereco_rua': row['Endereco'] if row['Endereco'] else 'NÃO INFORMADO',
                'endereco_numero': str(row['Num'])[:10] if row['Num'] else 'S/N',
                'endereco_bairro': row['Bairro'] if row['Bairro'] else 'CENTRO',
                'endereco_cidade': 'Uberlândia',
                'endereco_estado': 'MG',
                'tempo_moradia': map_choice(row['Tempomoradia'], Aluno.TEMPO_MORADIA_CHOICES, 'Mais de 5 anos'),
                'tipo_moradia': map_choice(row['Residencia'], Aluno.TIPO_MORADIA_CHOICES, 'Propria'),
                'valor_moradia': Decimal(str(row['ValorResidencia']).replace(',', '.')) if row['ValorResidencia'] and str(row['ValorResidencia']).lower() != 'nan' else Decimal('0.00'),
                'situacao_profissional': map_choice(row['Situacao'], Aluno.SITUACAO_PROFISSIONAL_CHOICES, 'Desempregado'),
                'renda_individual': Decimal(str(row['Renda']).replace(',', '.')) if row['Renda'] and str(row['Renda']).lower() != 'nan' else Decimal('0.00'),
                'num_moradores': int(row['NumMoradores']) if row['NumMoradores'] and str(row['NumMoradores']).isdigit() else 1,
                'quantos_trabalham': int(row['numtrabalham']) if row['numtrabalham'] and str(row['numtrabalham']).isdigit() else 0,
                'renda_moradores': Decimal(str(row['RendaTotal']).replace(',', '.')) if row['RendaTotal'] and str(row['RendaTotal']).lower() != 'nan' else Decimal('0.00'),
            }

            # Validar data de nascimento (obrigatória)
            if not aluno_data['data_nascimento']:
                print(f"Data Nasc Inválida para {row['Nome']} - Pulando.")
                skipped += 1
                continue

            # Buscar ou criar
            obj, created = Aluno.objects.update_or_create(
                cpf=raw_cpf, 
                escola=escola,
                defaults=aluno_data
            )
            
            if created:
                inserted += 1
            else:
                updated += 1

        except Exception as e:
            try:
                nome = dict(row).get('Nome', 'S/N')
            except Exception:
                nome = 'S/N'
            print(f"Erro ao processar linha {nome}: {e}")
            errors += 1

    conn.close()
    print(f"\n--- Resultado da Migração para {escola.nome} ---")
    print(f"Total no Backup: {total}")
    print(f"Novos Inseridos: {inserted}")
    print(f"Existentes Atualizados: {updated}")
    print(f"Pulados (Inválidos/Duplicados): {skipped}")
    print(f"Erros Fatais: {errors}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        # Default behavior
        print("Uso: python migrate_dirty_db.py <Nome_Escola> <Caminho_DB>")
        print("Utilizando padrão: CP Luizote / banco_cadastro.db")
        migrate("CP Luizote", "banco_cadastro.db")
    else:
        school = sys.argv[1]
        path = sys.argv[2]
        migrate(school, path)

