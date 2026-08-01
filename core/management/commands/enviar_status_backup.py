import logging
import os

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

DESTINATARIO_STATUS = 'klismanrds@gmail.com'
IDADE_MAXIMA_HORAS = 30  # backup roda 3x/dia; acima disso, algo parou
COR_VERDE = 3066993
COR_VERMELHA = 15158332


class Command(BaseCommand):
    help = (
        'Verifica o GCS e envia um e-mail periodico (a cada 3 dias, via cron) '
        'com o status do backup diario: Google Drive + Google Cloud Storage.'
    )

    def add_arguments(self, parser):
        parser.add_argument('drive_status', choices=['ok', 'falha'], help='Status do Drive, calculado fora (bash nao ve o container).')
        parser.add_argument('drive_detalhe', type=str, help='Detalhe textual do status do Drive.')

    def handle(self, *args, **options):
        drive_status = options['drive_status']
        drive_detalhe = options['drive_detalhe']

        gcs_status, gcs_detalhe = self._checar_gcs()

        tudo_ok = drive_status == 'ok' and gcs_status == 'ok'
        agora = timezone.localtime(timezone.now())

        if tudo_ok:
            assunto = f'[OK] Backup diario funcionando - {agora.strftime("%d/%m/%Y")}'
        else:
            assunto = f'[ALERTA] Backup diario com problema - {agora.strftime("%d/%m/%Y")}'

        corpo = (
            f'Checagem periodica do backup diario (Gestao Qualificacao Profissional), '
            f'{agora.strftime("%d/%m/%Y %H:%M")}.\n\n'
            f'Google Drive: {"OK" if drive_status == "ok" else "PROBLEMA"} — {drive_detalhe}\n'
            f'Google Cloud Storage: {"OK" if gcs_status == "ok" else "PROBLEMA"} — {gcs_detalhe}\n\n'
        )
        if tudo_ok:
            corpo += 'Nao precisa fazer nada — so um aviso de rotina de que esta tudo certo.'
        else:
            corpo += 'Pelo menos um dos destinos nao esta recebendo backup ha mais tempo do que o esperado. Vale checar.'

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'sistema@gestaoqualificacao.com.br')
        try:
            msg = EmailMultiAlternatives(
                subject=assunto,
                body=corpo,
                from_email=from_email,
                to=[DESTINATARIO_STATUS],
            )
            msg.send()
            self.stdout.write(self.style.SUCCESS('E-mail de status de backup enviado.'))
        except Exception as e:
            logger.exception('Falha ao enviar e-mail de status de backup.')
            self.stdout.write(self.style.ERROR(f'Erro ao enviar status: {e}'))

        self._notificar_discord(tudo_ok, drive_status, drive_detalhe, gcs_status, gcs_detalhe, agora)

    def _notificar_discord(self, tudo_ok, drive_status, drive_detalhe, gcs_status, gcs_detalhe, agora):
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if not webhook_url:
            return
        titulo = (
            f'✅ Checagem de backup (Gestão Profissional) OK - {agora.strftime("%d/%m/%Y")}'
            if tudo_ok else
            f'⚠️ Checagem de backup (Gestão Profissional) com problema - {agora.strftime("%d/%m/%Y")}'
        )
        descricao = (
            f'💾 Google Drive: {"✅ OK" if drive_status == "ok" else "❌ PROBLEMA"} — {drive_detalhe}\n'
            f'☁️ Google Cloud Storage: {"✅ OK" if gcs_status == "ok" else "❌ PROBLEMA"} — {gcs_detalhe}'
        )
        payload = {
            'embeds': [{
                'title': titulo,
                'description': descricao,
                'color': COR_VERDE if tudo_ok else COR_VERMELHA,
            }]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception:
            logger.exception('Falha ao notificar o Discord sobre o status do backup.')

    def _checar_gcs(self):
        try:
            from google.cloud import storage
            from google.oauth2 import service_account

            credentials = service_account.Credentials.from_service_account_file(
                '/app/google_drive_key.json'
            )
            client = storage.Client(credentials=credentials)
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blobs = sorted(bucket.list_blobs(), key=lambda b: b.time_created, reverse=True)

            if not blobs:
                return 'falha', 'Nenhum backup encontrado no bucket'

            idade_horas = (timezone.now() - blobs[0].time_created).total_seconds() / 3600
            if idade_horas > IDADE_MAXIMA_HORAS:
                return 'falha', f'Ultimo backup no GCS ha {idade_horas:.0f}h (esperado < {IDADE_MAXIMA_HORAS}h)'
            return 'ok', f'ultimo backup ha {idade_horas:.0f}h ({blobs[0].name})'
        except Exception as e:
            return 'falha', f'Erro ao acessar o GCS: {e}'
