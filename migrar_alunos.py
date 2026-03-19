import sqlite3
import os
import re
from datetime import datetime

# Se estiver sendo executado dentro do container Django (manage.py shell)
try:
    from alunos.models import Aluno
    from escolas.models import Escola
    from django.db import transaction
    IN_DJANGO = True
except ImportError:
    IN_DJANGO = False

def clean_cpf(cpf):
    if not cpf: return ""
    return re.sub(r'\D', '', str(cpf))

def parse_date(date_str):
    if not date_str or date_str in ['nan', '(null)', '']: return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(date_str, fmt).date()
        except: continue
    return None

def migrate(db_relative_path, escola_id):
    """
    db_relative_path: Caminho a partir da pasta '/app/Bancos dados/'
    exemplo: 'CP Morumbi/banco_cadastro.db'
    """
    if not IN_DJANGO:
        print("ERRO: Este script deve ser executado via 'python manage.py shell'")
        return

    base_folder = "/app/Bancos dados/"
    full_path = os.path.join(base_folder, db_relative_path)

    if not os.path.exists(full_path):
        print(f"!!! ARQUIVO NAO ENCONTRADO: {full_path}")
        return

    print(f"\n--- INICIANDO MIGRACAO: {db_relative_path} para Escola ID {escola_id} ---")
    
    try:
        conn = sqlite3.connect(full_path)
        conn.text_factory = bytes
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dados")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao acessar SQLite: {e}")
        return

    try:
        escola = Escola.objects.get(id=escola_id)
    except Escola.DoesNotExist:
        print(f"Erro: Escola com ID {escola_id} nao encontrada no Django.")
        conn.close()
        return

    c, u, e = 0, 0, 0
    
    with transaction.atomic():
        for row in rows:
            try:
                def get_val(key):
                    val = row[key]
                    if isinstance(val, bytes):
                        return val.decode('latin-1', errors='ignore').strip()
                    return str(val or '').strip()

                nome = get_val('Nome')
                if not nome: continue
                
                cpf = clean_cpf(get_val('Cpf'))
                data_nasc = parse_date(get_val('datanasc'))
                if not data_nasc:
                    data_nasc = datetime(1900, 1, 1).date()

                sexo = 'M' if 'MASC' in get_val('Sexo').upper() else 'F'
                
                renda_str = get_val('Renda').replace(',', '.')
                try: renda = float(renda_str)
                except: renda = 0

                if cpf and len(cpf) == 11:
                    aluno, created = Aluno.objects.update_or_create(
                        escola=escola,
                        cpf=cpf,
                        defaults={
                            'nome_completo': nome,
                            'data_nascimento': data_nasc,
                            'sexo': sexo,
                            'estado_civil': get_val('Estadocivil')[:20] or 'Solteiro',
                            'cor_raca': get_val('Cor')[:20] or 'Parda',
                            'nome_mae': get_val('Filiacao')[:255],
                            'endereco_cep': get_val('Cep')[:9] or '00000-000',
                            'endereco_rua': get_val('Endereco')[:255] or 'Nao informado',
                            'endereco_numero': get_val('Num')[:10] or 'S/N',
                            'endereco_bairro': get_val('Bairro')[:100] or 'Nao informado',
                            'endereco_cidade': 'Uberlandia',
                            'endereco_estado': 'MG',
                            'escolaridade': get_val('Escolaridade')[:50] or 'Fundamental Incompleto',
                            'situacao_profissional': get_val('Situacao')[:20] or 'Desempregado',
                            'renda_individual': renda,
                        }
                    )
                    if created: c += 1
                    else: u += 1
                else:
                    e += 1
            except Exception as ex:
                e += 1

    print(f"--- RESULTADO: Novos: {c} | Atualizados: {u} | Pulados/Erro: {e}")
    conn.close()

if __name__ == "__main__":
    # Exemplo: migrate("CP Morumbi/banco_cadastro.db", 8)
    pass
