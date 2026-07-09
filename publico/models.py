from django.db import models
from escolas.models import Escola


class BlocoConteudo(models.Model):
    TIPO_CHOICES = (
        ('texto', 'Texto Informativo'),
        ('curso', 'Curso do Mês'),
    )

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='blocos_conteudo')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='curso')
    titulo = models.CharField(max_length=200)
    texto = models.TextField(blank=True, help_text='Usado apenas se tipo=texto')
    data_inicio = models.DateField(null=True, blank=True, help_text='Usado apenas se tipo=curso')
    data_fim = models.DateField(null=True, blank=True, help_text='Usado apenas se tipo=curso')
    dias_semana = models.CharField(max_length=100, blank=True, help_text='Ex: Seg, Qua, Sex')
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    ordem = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordem', '-id']
        verbose_name = 'Bloco de Conteúdo'
        verbose_name_plural = 'Blocos de Conteúdo'

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.titulo} ({self.escola.nome})'

class CursoEmentaPublico(models.Model):
    titulo = models.CharField(max_length=200, verbose_name='Título do Curso')
    texto = models.TextField(verbose_name='Texto da Ementa')
    ativo = models.BooleanField(default=True, help_text='Exibir na página pública?')
    ordem = models.PositiveIntegerField(default=0, help_text='Usado para ordenar a lista')

    class Meta:
        ordering = ['ordem', 'titulo']
        verbose_name = 'Curso/Ementa Pública'
        verbose_name_plural = 'Cursos/Ementas Públicas'

    def __str__(self):
        return self.titulo
