from django.db import models
from django.conf import settings
from escolas.models import Escola
from datetime import date

class ControleDiario(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='controles_diarios')
    data = models.DateField(default=date.today)
    atendimento = models.IntegerField(default=0)
    inscricoes = models.IntegerField(default=0)
    pessoas_presentes = models.IntegerField(default=0)
    ligacoes_recebidas = models.IntegerField(default=0)
    ligacoes_realizadas = models.IntegerField(default=0)
    
    # Campo para registrar o usuário que fez o lançamento
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Controle Diário"
        verbose_name_plural = "Controles Diários"
        unique_together = ('escola', 'data') # Garante um único registro por escola por dia
        ordering = ['-data', 'escola__nome']

    def __str__(self):
        return f"Controle Diário de {self.escola.nome} em {self.data.strftime('%d/%m/%Y')}"