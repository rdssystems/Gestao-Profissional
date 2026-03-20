from django.db import models
from escolas.models import Escola


class WhatsAppConfig(models.Model):
    STATUS_CHOICES = [
        ('disconnected', 'Desconectado'),
        ('connecting', 'Conectando...'),
        ('connected', 'Conectado'),
        ('error', 'Erro'),
    ]

    escola = models.OneToOneField(
        Escola,
        on_delete=models.CASCADE,
        related_name='whatsapp_config'
    )
    instance_name = models.CharField(
        max_length=100,
        unique=True,
        help_text='Nome único da instância na Evolution API (ex: escola-morumbi)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='disconnected'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuração WhatsApp'
        verbose_name_plural = 'Configurações WhatsApp'

    def __str__(self):
        return f"WhatsApp - {self.escola.nome} ({self.get_status_display()})"
