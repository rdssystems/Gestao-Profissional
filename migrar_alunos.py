import sqlite3
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
    try: return float(str(val).replace(',', '.'))
    except: return 0

def clean_int(val):
    if not val or str(val).lower() in ['nan', '', ' ', 'null']: return 0
    try: return int(float(str(val)))
    except: return 0

def migrate(db_file_path, escola_name):
    if not IN_DJANGO:
        print("ERRO: Execute dentro do shell do Django.")
        return

    if not os.path.exists(db_file_path):
        print(f"❌ Arquivo não encontrado: {db_file_path}")
        return

    try:
        escola = Escola.objects.get(nome__iexact=escola_name)
    except Escola.DoesNotExist:
        print(f"❌ Escola '{escola_name}' não encontrada.")
        return

    print(f"\n--- 📦 Migrando: {db_file_path} -> {escola.nome} ---")
    
    try:
        conn = sqlite3.connect(db_file_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dados")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"⚠️ Erro ao ler SQLite: {e}")
        return

    c, u, e = 0, 0, 0
    
    with transaction.atomic():
        for row in rows:
            nome = ""
            try:
                def g(key):
                    try:
                        val = row[key]
                        if isinstance(val, bytes):
                            return val.decode('latin-1', errors='ignore').strip()
                        return str(val or '').strip()
                    except: return ""

                nome = g('Nome')
                cpf = clean_cpf(g('Cpf'))

                if not nome or not cpf:
                    e += 1
                    continue

                sexo = 'M' if 'MAS' in g('Sexo').upper() else 'F'
                
                ec_raw = g('Estadocivil').lower()
                estado_civil = 'Solteiro'
                if 'casad' in ec_raw: estado_civil = 'Casado'
                elif 'divorc' in ec_raw: estado_civil = 'Divorciado'
                elif 'viu' in ec_raw: estado_civil = 'Viúvo'
                elif 'uniao' in ec_raw or 'estavel' in ec_raw: estado_civil = 'Uniao Estavel'

                cor_raw = g('Cor').title()
                cor = cor_raw if cor_raw in ['Branca', 'Preta', 'Parda', 'Amarela', 'Indigena'] else 'Parda'

                esc_raw = g('Escolaridade').lower()
                escolaridade = 'Fundamental Incompleto'
                for opt in ['Analfabeto', 'Fundamental Incompleto', 'Fundamental Completo', 'Medio Incompleto', 'Medio Completo', 'Superior Incompleto', 'Superior Completo']:
                    if opt.lower() in esc_raw:
                        escolaridade = opt
                        break

                sit_raw = g('Situacao').title()
                situacao = 'Desempregado'
                for opt in ['Desempregado', 'Autonomo', 'Empregado', 'Estudante', 'Auxilio', 'INSS', 'Aposentado']:
                    if opt.lower() in sit_raw.lower():
                        situacao = opt
                        break

                mor_raw = g('Residencia').title()
                moradia = 'Propria'
                if 'Alug' in mor_raw: moradia = 'Alugada'
                elif 'Finan' in mor_raw: moradia = 'Financiada'
                elif 'Cedid' in mor_raw: moradia = 'Cedida'

                dt_nasc = parse_date(g('datanasc')) or datetime(1900, 1, 1).date()

                aluno, created = Aluno.objects.update_or_create(
                    escola=escola,
                    cpf=cpf,
                    defaults={
                        'nome_completo': nome,
                        'rg': g('Rg')[:20],
                        'orgao_exp': g('OrgaoEmissor')[:20],
                        'data_emissao': parse_date(g('DataEmissao')),
                        'data_nascimento': dt_nasc,
                        'sexo': sexo,
                        'estado_civil': estado_civil,
                        'cor_raca': cor,
                        'nome_mae': g('Filiacao')[:255],
                        'naturalidade': g('Cidaderesidencia')[:100],
                        'uf_naturalidade': g('Estado')[:2],
                        'deficiencia': ('SIM' in g('Deficiencia').upper() or g('Deficiencia') != ""),
                        'tipo_deficiencia': g('Deficiencia') if g('Deficiencia') != "Não" else "",
                        'escolaridade': escolaridade,
                        'email_principal': g('Email')[:100],
                        'whatsapp': g('Telefone1')[:20],
                        'telefone_principal': g('Telefone1')[:20] or g('Telefone2')[:20],
                        'endereco_cep': g('Cep')[:9] or '00000-000',
                        'endereco_rua': g('Endereco')[:255] or 'Nao informado',
                        'endereco_numero': g('Num')[:10] or 'S/N',
                        'endereco_bairro': g('Bairro')[:100] or 'Nao informado',
                        'endereco_cidade': 'Uberlandia',
                        'endereco_estado': 'MG',
                        'tempo_moradia': g('TempoUberlandia') if g('TempoUberlandia') in ['Natural', 'Menos de 5 anos', 'Mais de 5 anos'] else 'Mais de 5 anos',
                        'tipo_moradia': moradia,
                        'valor_moradia': clean_decimal(g('ValorResidencia')),
                        'situacao_profissional': situacao,
                        'renda_individual': clean_decimal(g('Renda')),
                        'num_moradores': clean_int(g('NumMoradores')),
                        'quantos_trabalham': clean_int(g('numtrabalham')),
                        'renda_moradores': clean_decimal(g('RendaTotal')) - clean_decimal(g('Renda')),
                        'observacoes': g('observacao')
                    }
                )
                if created: c += 1
                else: u += 1
            except Exception as ex:
                e += 1
    print(f"🟢 Concluído: {c} importados | {u} atualizados | {e} falhas.")
    conn.close()

if __name__ == "__main__":
    # Quando rodar no terminal VPS: 
    # Ex: migrate("/AppData/Gestao-Profissional/Bancos dados/CP Luizote/banco_cadastro.db", "CP Luizote")
    pass
