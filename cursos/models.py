from django.db import models
from escolas.models import Escola # Importar o modelo Escola
from datetime import date, time

class TipoCurso(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='tipos_curso')
    nome = models.CharField(max_length=100) # Nome do tipo de curso (ex: Informática)
    
    COR_CHOICES = (
        ('primary', 'Azul Principal'),
        ('secondary', 'Cinza Secundário'),
        ('success', 'Verde Sucesso'),
        ('danger', 'Vermelho Perigo'),
        ('warning', 'Amarelo Aviso'),
        ('info', 'Ciano Informação'),
        ('light', 'Cinza Claro'),
        ('dark', 'Preto Escuro'),
    )
    cor = models.CharField(max_length=20, choices=COR_CHOICES, default='primary', verbose_name="Cor")

    class Meta:
        verbose_name = "Tipo de Curso"
        verbose_name_plural = "Tipos de Curso"
        unique_together = ('escola', 'nome') # Garante que o nome do tipo de curso seja único por escola

    def __str__(self):
        return f"{self.nome} ({self.escola.nome})"

class Curso(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='cursos')
    tipo_curso = models.ForeignKey(TipoCurso, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos')
    STATUS_CHOICES = (
        ('Aberta', 'Aberta'),
        ('Em Andamento', 'Em Andamento'),
        ('Concluído', 'Concluído'),
    )
    nome = models.CharField(max_length=200)
    carga_horaria = models.IntegerField()
    data_inicio = models.DateField()
    data_fim = models.DateField()
    
    TURNOS_CHOICES = (
        ('Manhã', 'Manhã'),
        ('Tarde', 'Tarde'),
        ('Noite', 'Noite'),
    )
    turno = models.CharField(max_length=10, choices=TURNOS_CHOICES, blank=True, null=True)
    horario = models.TimeField(blank=True, null=True)
    horario_fim = models.TimeField(blank=True, null=True)

    DIAS_SEMANA_CHOICES = (
        ('Segunda', 'Segunda-feira'),
        ('Terça', 'Terça-feira'),
        ('Quarta', 'Quarta-feira'),
        ('Quinta', 'Quinta-feira'),
        ('Sexta', 'Sexta-feira'),
        ('Sábado', 'Sábado'),
        ('Domingo', 'Domingo'),
    )
    dia_inicio_semana = models.CharField(max_length=20, choices=DIAS_SEMANA_CHOICES, blank=True, null=True)
    dia_fim_semana = models.CharField(max_length=20, choices=DIAS_SEMANA_CHOICES, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return self.nome

class Inscricao(models.Model):
    aluno = models.ForeignKey('alunos.Aluno', on_delete=models.CASCADE)
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    
    STATUS_CHOICES = (
        ('cursando', 'Cursando'),
        ('concluido', 'Concluído'),
        ('desistente', 'Desistente'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='cursando', verbose_name="Status")

    def __str__(self):
        return f'{self.aluno.nome_completo} - {self.curso.nome}'


# --- Novos modelos para Frequência ---

class RegistroAula(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='registros_aula', verbose_name="Curso")
    data_aula = models.DateField(verbose_name="Data da Aula", default=date.today)
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Registro de Aula"
        verbose_name_plural = "Registros de Aulas"
        unique_together = ('curso', 'data_aula') # Garante que só pode haver uma aula por curso por dia
        ordering = ['-data_aula']

    def __str__(self):
        return f"Aula de {self.curso.nome} em {self.data_aula.strftime('%d/%m/%Y')}"

class Chamada(models.Model):
    registro_aula = models.ForeignKey(RegistroAula, on_delete=models.CASCADE, related_name='chamadas', verbose_name="Registro de Aula")
    inscricao = models.ForeignKey(Inscricao, on_delete=models.CASCADE, related_name='chamadas', verbose_name="Inscrição")
    
    STATUS_PRESENCA_CHOICES = (
        ('P', 'Presente'),
        ('A', 'Ausente'),
        ('J', 'Ausência Justificada'),
    )
    status_presenca = models.CharField(max_length=1, choices=STATUS_PRESENCA_CHOICES, default='A', verbose_name="Status de Presença")

    class Meta:
        verbose_name = "Chamada"
        verbose_name_plural = "Chamadas"
        unique_together = ('registro_aula', 'inscricao') # Um aluno só pode ter um registro de presença por aula
        ordering = ['inscricao__aluno__nome_completo']

    def __str__(self):
        return f"{self.inscricao.aluno.nome_completo} - {self.get_status_presenca_display()}"