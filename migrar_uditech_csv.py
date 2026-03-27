import csv
import os
import re
from datetime import datetime
from django.db import transaction

# Modelos do Django
try:
    from alunos.models import Aluno
    from escolas.models import Escola
    IN_DJANGO = True
except ImportError:
    IN_DJANGO = False

def clean_cpf(cpf):
    if not cpf: return ""
    digits = re.sub(r'\D', '', str(cpf))
    return digits if len(digits) == 11 else ""

def parse_date(date_str):
    if not date_str or str(date_str).lower() in ['nan', '(null)', '', ' ', 'null']: return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y'):
        try: return datetime.strptime(date_str.strip(), fmt).date()
        except: continue
    return None

def clean_decimal(val):
    if not val or str(val).lower() in ['nan', '', ' ', 'null']: return 0
    try: 
        # Remove R$, pontos de milhar e troca vírgula por ponto
        s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(s)
    except: return 0

def clean_int(val):
    if not val or str(val).lower() in ['nan', '', ' ', 'null']: return 0
    try: return int(float(str(val)))
    except: return 0

def map_sexo(val):
    val = str(val).upper()
    if 'FEM' in val: return 'F'
    if 'MAS' in val: return 'M'
    return 'F' # Default

def map_escolaridade(val):
    v = str(val).lower()
    if 'pós' in v or 'pos' in v: return 'Superior Completo'
    if 'superior' in v:
        return 'Superior Incompleto' if 'incompleto' in v else 'Superior Completo'
    if 'médio' in v or 'medio' in v:
        return 'Medio Incompleto' if 'incompleto' in v else 'Medio Completo'
    if 'fundamental' in v:
        return 'Fundamental Incompleto' if 'incompleto' in v else 'Fundamental Completo'
    return 'Fundamental Incompleto'

def map_estado_civil(val):
    v = str(val).lower()
    if 'casad' in v: return 'Casado'
    if 'divorc' in v: return 'Divorciado'
    if 'viu' in v: return 'Viúvo'
    if 'uniao' in v or 'estavel' in v: return 'Uniao Estavel'
    return 'Solteiro'

def migrate_csv(csv_path, escola_name):
    if not IN_DJANGO:
        print("ERRO: Execute dentro do shell do Django (python manage.py shell).")
        return

    if not os.path.exists(csv_path):
        print(f"❌ Arquivo não encontrado: {csv_path}")
        return

    try:
        escola = Escola.objects.get(nome__iexact=escola_name)
    except Escola.DoesNotExist:
        print(f"❌ Escola '{escola_name}' não encontrada.")
        return

    print(f"\n--- 📦 Migrando CSV: {csv_path} -> {escola.nome} ---")
    
    c, u, e = 0, 0, 0
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            # Note o delimitador ; conforme análise prévia
            reader = csv.DictReader(f, delimiter=';')
            rows = list(reader)
    except Exception as ex:
        print(f"⚠️ Erro ao ler CSV: {ex}")
        return

    with transaction.atomic():
        for row in rows:
            try:
                # Mapeamento de colunas baseado nos cabeçalhos reais (com dois pontos)
                nome = row.get('Nome Completo:', '').strip()
                cpf_raw = row.get('CPF: (Somente Números)', '')
                cpf = clean_cpf(cpf_raw)

                if not nome or not cpf:
                    print(f"⚠️ Pulando registro sem Nome ou CPF válido: {nome} | {cpf_raw}")
                    e += 1
                    continue

                # Naturalidade: "CIDADE/UF"
                nat_raw = row.get('Naturalidade: \nCIDADE/UF', row.get('Naturalidade: CIDADE/UF', ''))
                naturalidade = nat_raw.split('/')[0].strip()[:100] if '/' in nat_raw else nat_raw[:100]
                uf_nat = nat_raw.split('/')[1].strip()[:2] if '/' in nat_raw else 'MG'

                # Observações consolidadas
                obs_parts = []
                if row.get('Você recebe algum benefício do Governo?'):
                    obs_parts.append(f"Benefício: {row.get('Você recebe algum benefício do Governo?')} ({row.get('Se sim, qual?')})")
                if row.get('Por onde você ficou sabendo sobre nossos cursos?'):
                    obs_parts.append(f"Soube por: {row.get('Por onde você ficou sabendo sobre nossos cursos?')}")
                if row.get('Qual seu canal de comunicação de preferência?'):
                    obs_parts.append(f"Canal preferência: {row.get('Qual seu canal de comunicação de preferência?')}")
                
                observacoes = " | ".join(obs_parts)

                aluno, created = Aluno.objects.update_or_create(
                    escola=escola,
                    cpf=cpf,
                    defaults={
                        'nome_completo': nome,
                        'data_nascimento': parse_date(row.get('Data de Nascimento:')) or datetime(1900, 1, 1).date(),
                        'email_principal': row.get('E-mail:', '')[:100],
                        'nome_mae': row.get('Nome da Mãe:', '')[:255],
                        'sexo': map_sexo(row.get('Sexo:', 'F')),
                        'estado_civil': map_estado_civil(row.get('Estado Civil:', 'Solteiro')),
                        'cor_raca': row.get('Cor/Raça:', 'Parda').strip().title()[:20],
                        'naturalidade': naturalidade,
                        'uf_naturalidade': uf_nat,
                        'endereco_rua': row.get('Endereço:', 'Não informado')[:255],
                        'endereco_bairro': row.get('Bairro:', 'Não informado')[:100],
                        'endereco_cep': re.sub(r'\D', '', row.get('CEP (somente números)', ''))[:9] or '00000-000',
                        'telefone_principal': re.sub(r'\D', '', row.get('Telefone para contato:', ''))[:20],
                        'whatsapp': re.sub(r'\D', '', row.get('Telefone para contato:', ''))[:20],
                        'rg': row.get('RG:', '')[:20],
                        'data_emissao': parse_date(row.get('Data de Emissão do RG:')),
                        'orgao_exp': row.get('Órgão Emissor: ', '')[:20],
                        'escolaridade': map_escolaridade(row.get('Escolaridade: (Pós-graduação; Superior; Médio; Fundamental)', '')),
                        'situacao_profissional': row.get('Situação Profissional:', 'Desempregado').split('(')[0].strip().title()[:20],
                        'num_moradores': clean_int(row.get('Quantas pessoas moram com você?')),
                        'quantos_trabalham': clean_int(row.get('Dentre essas pessoas, quantas recebem renda?')),
                        'renda_moradores': clean_decimal(row.get('Qual o valor médio da renda mensal de sua família?')),
                        'tipo_moradia': 'Alugada' if 'Alugada' in row.get('A casa onde você mora é:', '') else 'Propria',
                        'valor_moradia': clean_decimal(row.get('Se for alugada, qual o valor do aluguel?')),
                        'endereco_cidade': 'Uberlândia',
                        'endereco_estado': 'MG',
                        'endereco_numero': 'S/N',
                        'observacoes': observacoes
                    }
                )
                if created: c += 1
                else: u += 1
            except Exception as ex:
                print(f"❌ Erro na linha {row.get('Nome Completo:', 'UNK')}: {ex}")
                e += 1

    print(f"\n✅ Migração concluída!")
    print(f"   - Criados: {c}")
    print(f"   - Atualizados: {u}")
    print(f"   - Falhas: {e}")

if __name__ == "__main__":
    # Exemplo de uso no shell:
    # from migrar_uditech_csv import migrate_csv
    # migrate_csv("INSCRICROES_UDITECH.csv", "Uditech")
    pass
