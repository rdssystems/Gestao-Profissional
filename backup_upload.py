#!/usr/bin/env python3
"""
Script de upload de backup para o Google Cloud Storage.
Roda DENTRO do container gq-app, que já tem as bibliotecas da Google instaladas.
"""
import sys
import os

# Configura o Django para acessar as settings
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')

import django
django.setup()

from django.conf import settings
from google.cloud import storage
from google.oauth2 import service_account


def upload_and_cleanup(filename):
    local_path = f'/tmp/{filename}'

    # Carrega as credenciais
    credentials = service_account.Credentials.from_service_account_file(
        '/app/google_drive_key.json'
    )

    bucket_name = settings.GS_BUCKET_NAME
    client = storage.Client(credentials=credentials)
    bucket = client.bucket(bucket_name)

    # Faz o upload do arquivo
    print(f"    Fazendo upload de '{filename}' para o bucket '{bucket_name}'...")
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_path)
    print(f"    Upload concluído!")

    # Política de retenção: mantém apenas os 20 mais recentes
    blobs = sorted(bucket.list_blobs(), key=lambda b: b.time_created)
    if len(blobs) > 20:
        to_delete = blobs[:-20]
        for b in to_delete:
            b.delete()
            print(f"    Backup antigo removido: {b.name}")
    else:
        print(f"    Total de backups no bucket: {len(blobs)} (dentro do limite de 20).")

    # Limpa o arquivo temporário dentro do container
    if os.path.exists(local_path):
        os.remove(local_path)
        print(f"    Arquivo temporário removido do container.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python backup_upload.py <nome_do_arquivo>")
        sys.exit(1)

    filename = sys.argv[1]
    upload_and_cleanup(filename)
