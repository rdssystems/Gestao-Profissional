import uuid
from django.db import models
from escolas.models import Escola # Importar o modelo Escola
from datetime import date, time
from django.utils.translation import gettext_lazy as _

class EmentaPadrao(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título da Ementa")
    conteudo = models.TextField(verbose_name="Conteúdo Programático")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ementa Padrão"
        verbose_name_plural = "Ementas Padrão"
        ordering = ['titulo']

    def __str__(self):
        return self.titulo

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
        ('indigo', 'Anil (Indigo)'),
        ('purple', 'Roxo'),
        ('pink', 'Rosa'),
        ('orange', 'Laranja'),
        ('teal', 'Verde Água (Teal)'),
    )
    cor = models.CharField(max_length=20, choices=COR_CHOICES, default='primary', verbose_name="Cor")
    ementa = models.ForeignKey(EmentaPadrao, on_delete=models.SET_NULL, null=True, blank=True, related_name='tipos_curso', verbose_name="Ementa Padrão")

    class Meta:
        verbose_name = "Tipo de Curso"
        verbose_name_plural = "Tipos de Curso"
        unique_together = ('escola', 'nome') # Garante que o nome do tipo de curso seja único por escola

    def __str__(self):
        return f"{self.nome} ({self.escola.nome})"

class Parceiro(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='parceiros')
    nome = models.CharField(max_length=200, verbose_name="Nome do Parceiro")

    class Meta:
        verbose_name = "Parceiro"
        verbose_name_plural = "Parceiros"
        unique_together = ('escola', 'nome')

    def __str__(self):
        return f"{self.nome} ({self.escola.nome})"

class Curso(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='cursos')
    tipo_curso = models.ForeignKey(TipoCurso, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos')
    STATUS_CHOICES = (
        ('Aberta', 'Aberta'),
        ('Em Andamento', 'Em Andamento'),
        ('Concluído', 'Concluído'),
        ('Arquivado', 'Arquivado'), # Novo status
    )
    nome = models.CharField(max_length=200)
    carga_horaria = models.IntegerField()
    vagas = models.PositiveIntegerField(default=0, verbose_name="Número de Vagas")
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

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Aberta')
    nome_professor = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nome do Professor")
    parceiro = models.ForeignKey(Parceiro, on_delete=models.SET_NULL, null=True, blank=True, related_name='cursos', verbose_name="Parceiro")
    token_acesso = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="Token de Acesso")

    def __str__(self):
        return self.nome

    @property
    def total_inscritos(self):
        # Considera apenas inscrições ativas (cursando) para a taxa de ocupação
        return self.inscricao_set.filter(status='cursando').count()

    @property
    def total_concluidos(self):
        # Considera apenas inscrições concluídas
        return self.inscricao_set.filter(status='concluido').count()

    @property
    def taxa_ocupacao(self):
        if self.vagas > 0:
            return min(100, int((self.total_inscritos / self.vagas) * 100))
        return 0

    @property
    def check_avaliacao_50_percent(self):
        total_alunos_ativos = self.inscricao_set.exclude(status='desistente').count()
        if total_alunos_ativos == 0:
            return False
        total_avaliacoes = self.inscricao_set.filter(avaliacao_professor__isnull=False).count()
        return (total_avaliacoes / total_alunos_ativos) >= 0.5

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

    @property
    def total_presencas(self):
        return len([c for c in self.chamadas.all() if c.status_presenca == 'P'])

    @property
    def total_faltas(self):
        return len([c for c in self.chamadas.all() if c.status_presenca != 'P'])

    @property
    def frequencia_porcentagem(self):
        total = len(self.chamadas.all())
        if total > 0:
            return int((self.total_presencas / total) * 100)
        return 100


# --- Novos modelos para Frequência ---

class RegistroAula(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='registros_aula', verbose_name="Curso")
    data_aula = models.DateField(verbose_name="Data da Aula", default=date.today)
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    nao_houve_aula = models.BooleanField(default=False, verbose_name="Não houve aula (Feriado/Recesso)")

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

    STATUS_PRESENCA_CHOICES = (
        ('P', 'Presente'),
        ('A', 'Ausente'),
        ('J', 'Ausência Justificada'),
    )

    MOTIVO_FALTA_CHOICES = (
        ('Medico', 'Médico'),
        ('Doenca', 'Doença'),
        ('Trabalho', 'Trabalho'),
        ('Escola', 'Escola'),
        ('Transporte', 'Transporte'),
        ('Familia', 'Problemas Familiares'),
        ('Viagem', 'Viagem'),
        ('Luto', 'Falecimento'),
        ('Consulta', 'Consulta Médica'),
        ('Outros', 'Outros'),
    )

    status_presenca = models.CharField(max_length=1, choices=STATUS_PRESENCA_CHOICES, default='A', verbose_name="Status de Presença")
    motivo_falta = models.CharField(max_length=20, choices=MOTIVO_FALTA_CHOICES, blank=True, null=True, verbose_name="Motivo da Falta")
    motivo_falta_outro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Outro Motivo")

    class Meta:
        verbose_name = "Chamada"
        verbose_name_plural = "Chamadas"
        unique_together = ('registro_aula', 'inscricao') # Um aluno só pode ter um registro de presença por aula
        ordering = ['inscricao__aluno__nome_completo']

    def __str__(self):
        return f"{self.inscricao.aluno.nome_completo} - {self.get_status_presenca_display()}"


# --- Novos modelos para Avaliações ---

VALOR_CHOICES = (
    ('Otimo', 'Ótimo'),
    ('Bom', 'Bom'),
    ('Regular', 'Regular'),
)

class AvaliacaoProfessorAluno(models.Model):
    """Ficha de avaliação de desempenho do aluno preenchida pelo professor"""
    inscricao = models.OneToOneField(Inscricao, on_delete=models.CASCADE, related_name='avaliacao_professor', verbose_name="Inscrição")
    professor_nome = models.CharField(max_length=200, verbose_name="Nome do Professor")
    data_preenchimento = models.DateTimeField(auto_now_add=True)

    # Seção: Conceitual
    conceptual_pratico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Conceitual - Prático")
    conceptual_teorico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Conceitual - Teórico")
    conceptual_nota = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Conceitual - Nota")

    # Seção: Comportamental
    behavioral_pratico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Assiduidade e Pontualidade")
    behavioral_teorico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Interesse e Participação")
    behavioral_nota = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Apresentação Pessoal")

    # Seção: Atitudinal
    attitudinal_pratico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Atitudinal - Relacionamento Interpessoal")
    attitudinal_teorico = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Atitudinal - Comunicação")
    attitudinal_nota = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Atitudinal - Criatividade")

    class Meta:
        verbose_name = "Avaliação do Professor (Aluno)"
        verbose_name_plural = "Avaliações do Professor (Alunos)"

    def __str__(self):
        return f"Desempenho: {self.inscricao.aluno.nome_completo} ({self.inscricao.curso.nome})"

class AvaliacaoAlunoCurso(models.Model):
    """Ficha de avaliação do curso preenchida pelo aluno"""
    inscricao = models.OneToOneField(Inscricao, on_delete=models.CASCADE, related_name='avaliacao_aluno', verbose_name="Inscrição")
    data_preenchimento = models.DateTimeField(auto_now_add=True)

    # 1 - Quanto ao Conteúdo
    c1_1 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Conteúdo cumprido")
    c1_2 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Material didático")
    c1_3 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Recursos audiovisuais")

    # 2 - Quanto ao Instrutor
    c2_1 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Conhecimento do Instrutor")
    c2_2 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Forma de ensinar")
    c2_3 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Estímulo à participação")
    c2_4 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Objetividade e Clareza")
    c2_5 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Técnicas de ensino")
    c2_6 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Esclarecimento de dúvidas")
    c2_7 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Atenção às solicitações")
    c2_8 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Cumprimento de horários")
    c2_9 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Assiduidade (Presença)")

    # 3 - Quanto ao Espaço Físico e Organização
    c3_1 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Espaço e Instalações")
    c3_2 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Facilidade na inscrição")
    c3_3 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Atendimento da coordenação")
    c3_4 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Carga horária adequada")

    # 4 - Auto Avaliação
    c4_1 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Aprendizado adquirido")
    c4_2 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Pontualidade própria")
    c4_3 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Minha participação")
    c4_4 = models.CharField(max_length=10, choices=VALOR_CHOICES, verbose_name="Relacionamento com colegas")

    # 5 - Divulgação
    DIVULGACAO_CHOICES = (
        ('Cartaz', 'Cartaz, folder'),
        ('Internet', 'Internet'),
        ('Jornal', 'Jornal'),
        ('Televisao', 'Televisão'),
        ('Outros', 'Outros'),
    )
    como_soube = models.CharField(max_length=20, choices=DIVULGACAO_CHOICES, verbose_name="Como soube")
    como_soube_outro = models.CharField(max_length=100, blank=True, null=True, verbose_name="Outros divulgação")

    # 6 - Comentários e Sugestões
    comentarios = models.TextField(blank=True, null=True, verbose_name="Comentários/Sugestões")

    class Meta:
        verbose_name = "Avaliação do Aluno (Curso)"
        verbose_name_plural = "Avaliações do Aluno (Cursos)"

    def __str__(self):
        return f"Satisfação: {self.inscricao.aluno.nome_completo} ({self.inscricao.curso.nome})"