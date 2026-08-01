import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

DESTINATARIO_ALERTA = 'klismanrds@gmail.com'


class Command(BaseCommand):
    help = (
        'Envia um e-mail de alerta quando o backup diario do banco de dados '
        'falha em todos os destinos configurados (Google Drive e GCS).'
    )

    def add_arguments(self, parser):
        parser.add_argument('mensagem', type=str, help='Detalhes do que falhou.')

    def handle(self, *args, **options):
        mensagem = options['mensagem']
        agora = timezone.localtime(timezone.now())
        assunto = f'[ALERTA] Backup diario falhou - {agora.strftime("%d/%m/%Y %H:%M")}'
        corpo = (
            'O backup diario do banco de dados (Gestao Qualificacao Profissional) '
            'falhou em TODOS os destinos configurados (Google Drive e Google Cloud '
            'Storage) no mesmo ciclo.\n\n'
            f'Detalhes:\n{mensagem}\n\n'
            'Verifique o arquivo backup_gcs.log na VPS '
            '(/DATA/AppData/Gestao-Profissional/backup_gcs.log) assim que possivel.'
        )
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'sistema@gestaoqualificacao.com.br')
        try:
            msg = EmailMultiAlternatives(
                subject=assunto,
                body=corpo,
                from_email=from_email,
                to=[DESTINATARIO_ALERTA],
            )
            msg.send()
            self.stdout.write(self.style.SUCCESS('Alerta de falha de backup enviado.'))
        except Exception as e:
            logger.exception('Falha ao enviar e-mail de alerta de backup.')
            self.stdout.write(self.style.ERROR(f'Erro ao enviar alerta: {e}'))
