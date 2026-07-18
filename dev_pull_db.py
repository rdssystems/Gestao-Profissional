#!/usr/bin/env python3
"""
Baixa o banco de dados atual da VPS para uso no ambiente de desenvolvimento local.
Uso: python dev_pull_db.py
"""
import paramiko, sys, os, subprocess

# Credenciais lidas do ambiente (nunca versionar segredos).
# Defina antes de rodar, ex:
#   export VPS_HOST=... VPS_USER=... VPS_PASS=...
VPS_HOST = os.getenv('VPS_HOST')
VPS_USER = os.getenv('VPS_USER')
VPS_PASS = os.getenv('VPS_PASS')
VPS_PORT = int(os.getenv('VPS_PORT', '22'))
LOCAL_DUMP = 'dev_restore.dump'

if not all([VPS_HOST, VPS_USER, VPS_PASS]):
    sys.exit(
        'Erro: defina as variaveis de ambiente VPS_HOST, VPS_USER e VPS_PASS '
        'antes de executar este script.'
    )

print('Conectando à VPS...')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER, password=VPS_PASS, timeout=15)

def run(cmd, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    return stdout.read().decode('utf-8', errors='replace'), stderr.read().decode('utf-8', errors='replace')

print('Gerando dump do banco de produção...')
run(f'echo "{VPS_PASS}" | sudo -S docker exec gq-db pg_dump -U gestao_user -Fc gestao_db > /tmp/dev_restore.dump')

out, _ = run('ls -lh /tmp/dev_restore.dump')
print('Tamanho no servidor:', out.strip().split()[4] if out.strip() else '?')

print('Baixando...')
sftp = client.open_sftp()
sftp.get('/tmp/dev_restore.dump', LOCAL_DUMP)
sftp.close()
run('rm /tmp/dev_restore.dump')
client.close()

size_mb = os.path.getsize(LOCAL_DUMP) / 1024 / 1024
print(f'Download concluído: {size_mb:.1f} MB → {LOCAL_DUMP}')
print()
print('Para restaurar no banco local, execute:')
print('  bash dev_restore_db.sh')
