#!/usr/bin/env python3
"""
Baixa o banco de dados atual da VPS para uso no ambiente de desenvolvimento local.
Uso: python dev_pull_db.py
"""
import paramiko, sys, os, subprocess

VPS_HOST = '100.76.30.36'
VPS_USER = 'klismanrds'
VPS_PASS = '32166096'
LOCAL_DUMP = 'dev_restore.dump'

print('Conectando à VPS...')
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(VPS_HOST, port=22, username=VPS_USER, password=VPS_PASS, timeout=15)

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
