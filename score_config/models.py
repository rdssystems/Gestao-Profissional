from django.db import models
from alunos.models import Aluno

class FaixaScoreBase(models.Model):
    """
    Modelo base abstrato para faixas de score.
    """
    pontos = models.IntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['-pontos']

class RendaFamiliarFaixa(FaixaScoreBase):
    valor_maior_que = models.DecimalField(max_digits=10, decimal_places=2, help_text="A pontuação será aplicada se a renda familiar for MAIOR QUE este valor.")

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Renda Familiar"
        verbose_name_plural = "1. Faixas de Renda Familiar"
        ordering = ['-valor_maior_que']

    def __str__(self):
        return f"Se renda familiar > R$ {self.valor_maior_que}, ganha {self.pontos} pontos"

class RendaPerCapitaFaixa(FaixaScoreBase):
    valor_maior_que = models.DecimalField(max_digits=10, decimal_places=2, help_text="A pontuação será aplicada se a renda per capita for MAIOR QUE este valor.")

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Renda Per Capita"
        verbose_name_plural = "2. Faixas de Renda Per Capita"
        ordering = ['-valor_maior_que']

    def __str__(self):
        return f"Se renda per capita > R$ {self.valor_maior_que}, ganha {self.pontos} pontos"

class NumeroMoradoresFaixa(FaixaScoreBase):
    qtd_maior_ou_igual = models.IntegerField(help_text="A pontuação será aplicada se o número de moradores for MAIOR OU IGUAL A este valor.")

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Número de Moradores"
        verbose_name_plural = "3. Faixas de Número de Moradores"
        ordering = ['-qtd_maior_ou_igual']

    def __str__(self):
        return f"Se Nº de moradores >= {self.qtd_maior_ou_igual}, ganha {self.pontos} pontos"

class MembrosTrabalhamFaixa(FaixaScoreBase):
    qtd_maior_ou_igual = models.IntegerField(help_text="A pontuação será aplicada se a quantidade de membros que trabalham for MAIOR OU IGUAL A este valor.")

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Membros que Trabalham"
        verbose_name_plural = "4. Faixas de Membros que Trabalham"
        ordering = ['-qtd_maior_ou_igual']

    def __str__(self):
        return f"Se membros que trabalham >= {self.qtd_maior_ou_igual}, ganha {self.pontos} pontos"

class TempoMoradiaFaixa(FaixaScoreBase):
    titulo = models.CharField(max_length=20, choices=Aluno.TEMPO_MORADIA_CHOICES, unique=True)

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Tempo de Moradia"
        verbose_name_plural = "5. Faixas de Tempo de Moradia"
        ordering = ['titulo']

    def __str__(self):
        return f"Se tempo de moradia for '{self.get_titulo_display()}', ganha {self.pontos} pontos"

class TipoMoradiaFaixa(FaixaScoreBase):
    titulo = models.CharField(max_length=20, choices=Aluno.TIPO_MORADIA_CHOICES, unique=True)

    class Meta(FaixaScoreBase.Meta):
        verbose_name = "Faixa de Tipo de Moradia"
        verbose_name_plural = "6. Faixas de Tipo de Moradia"
        ordering = ['titulo']

    def __str__(self):
        return f"Se tipo de moradia for '{self.get_titulo_display()}', ganha {self.pontos} pontos"