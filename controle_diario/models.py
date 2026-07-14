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


class RelatorioDiarioSine(models.Model):
    data = models.DateField(default=date.today, unique=True, verbose_name="Data do Relatório")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Lançado por")
    
    # Atendimentos
    atendimento_trabalhador = models.PositiveIntegerField(default=0, verbose_name="Atendimento ao Trabalhador")
    atendimento_trabalhador_online = models.PositiveIntegerField(default=0, verbose_name="Atendimento ao Trabalhador On-line")
    atendimento_empregador = models.PositiveIntegerField(default=0, verbose_name="Atendimento ao Empregador")
    atendimento_empregador_online = models.PositiveIntegerField(default=0, verbose_name="Atendimento ao Empregador On-line")
    
    # Serviços
    seguro_desemprego = models.PositiveIntegerField(default=0, verbose_name="Seguro Desemprego")
    ctps_digital = models.PositiveIntegerField(default=0, verbose_name="CTPS Digital")
    
    # Intermediação
    vagas_captadas = models.PositiveIntegerField(default=0, verbose_name="Vagas Captadas")
    curriculos = models.PositiveIntegerField(default=0, verbose_name="Currículos")
    entrevistados = models.PositiveIntegerField(default=0, verbose_name="Entrevistados")
    processo_seletivo = models.PositiveIntegerField(default=0, verbose_name="Processo Seletivo")
    orientacao_profissional = models.PositiveIntegerField(default=0, verbose_name="Orientação Profissional")
    
    # Telefonia
    ligacoes_recebidas = models.PositiveIntegerField(default=0, verbose_name="Número de Ligações Recebidas")
    ligacoes_realizadas = models.PositiveIntegerField(default=0, verbose_name="Número de Ligações Realizadas")

    class Meta:
        verbose_name = "Relatório Diário do SINE"
        verbose_name_plural = "Relatórios Diários do SINE"
        ordering = ['-data']

    def __str__(self):
        return f"SINE - {self.data.strftime('%d/%m/%Y')}"

    @property
    def total_procedimentos(self):
        return (
            self.atendimento_trabalhador + self.atendimento_trabalhador_online +
            self.atendimento_empregador + self.atendimento_empregador_online +
            self.seguro_desemprego + self.ctps_digital + self.vagas_captadas +
            self.ligacoes_recebidas + self.ligacoes_realizadas + self.curriculos +
            self.entrevistados + self.processo_seletivo + self.orientacao_profissional
        )