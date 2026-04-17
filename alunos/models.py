from django.db import models
from escolas.models import Escola
from cursos.models import TipoCurso
from datetime import date

class Aluno(models.Model):
    # Relacionamentos
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='alunos', verbose_name="Escola")
    cursos_interesse = models.ManyToManyField(TipoCurso, blank=True, verbose_name="Cursos de Interesse")

    # Identificação
    nome_completo = models.CharField(max_length=255, verbose_name="Nome Completo")
    cpf = models.CharField(max_length=14, verbose_name="CPF")
    rg = models.CharField(max_length=20, blank=True, null=True, verbose_name="RG")
    orgao_exp = models.CharField(max_length=20, blank=True, null=True, verbose_name="Órgão Expedidor")
    data_emissao = models.DateField(blank=True, null=True, verbose_name="Data de Emissão")

    class Meta:
        unique_together = ('escola', 'cpf')

    # Nascimento
    data_nascimento = models.DateField(verbose_name="Data de Nascimento")

    @property
    def idade(self):
        today = date.today()
        return today.year - self.data_nascimento.year - ((today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day))

    # Informações Sociais
    SEXO_CHOICES = (('M', 'Masculino'), ('F', 'Feminino'))
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, verbose_name="Sexo")
    
    ESTADO_CIVIL_CHOICES = (('Solteiro', 'Solteiro'), ('Casado', 'Casado'), ('Divorciado', 'Divorciado'), ('Viúvo', 'Viúvo'), ('Uniao Estavel', 'União Estável'))
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, verbose_name="Estado Civil")

    COR_RACA_CHOICES = (('Branca', 'Branca'), ('Preta', 'Preta'), ('Parda', 'Parda'), ('Amarela', 'Amarela'), ('Indigena', 'Indígena'))
    cor_raca = models.CharField(max_length=20, choices=COR_RACA_CHOICES, blank=True, null=True, verbose_name="Cor/Raça")
    
    nome_mae = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome da Mãe")
    naturalidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Naturalidade")
    uf_naturalidade = models.CharField(max_length=2, blank=True, null=True, verbose_name="UF da Naturalidade")
    
    deficiencia = models.BooleanField(default=False, verbose_name="Possui alguma deficiência?")
    tipo_deficiencia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qual a deficiência?")
    
    # ...
    # (Existing fields continue)

    ESCOLARIDADE_CHOICES = (
        ('Analfabeto', 'Analfabeto'),
        ('Fundamental Incompleto', 'Fundamental Incompleto'),
        ('Fundamental Completo', 'Fundamental Completo'),
        ('Medio Incompleto', 'Médio Incompleto'),
        ('Medio Completo', 'Médio Completo'),
        ('Superior Incompleto', 'Superior Incompleto'),
        ('Superior Completo', 'Superior Completo'),
    )
    escolaridade = models.CharField(max_length=50, choices=ESCOLARIDADE_CHOICES, blank=True, null=True, verbose_name="Escolaridade")

    # Contato
    email_principal = models.EmailField(blank=True, null=True, verbose_name="Email Principal")
    whatsapp = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp")
    telefone_principal = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone Principal")

    # Endereço
    endereco_cep = models.CharField(max_length=9, verbose_name="CEP")
    endereco_rua = models.CharField(max_length=255, verbose_name="Endereço")
    endereco_numero = models.CharField(max_length=10, verbose_name="Número")
    endereco_bairro = models.CharField(max_length=100, verbose_name="Bairro")
    endereco_cidade = models.CharField(max_length=100, verbose_name="Cidade")
    endereco_estado = models.CharField(max_length=2, verbose_name="Estado")
    
    TEMPO_MORADIA_CHOICES = (('Natural', 'Natural'), ('Menos de 5 anos', 'Menos de 5 anos'), ('Mais de 5 anos', 'Mais de 5 anos'))
    tempo_moradia = models.CharField(max_length=20, choices=TEMPO_MORADIA_CHOICES, blank=True, null=True, verbose_name="Tempo de Moradia")
    
    TIPO_MORADIA_CHOICES = (('Propria', 'Própria'), ('Financiada', 'Financiada'), ('Alugada', 'Alugada'), ('Cedida', 'Cedida'))
    tipo_moradia = models.CharField(max_length=20, choices=TIPO_MORADIA_CHOICES, blank=True, null=True, verbose_name="Tipo de Moradia")
    valor_moradia = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Valor da Moradia")

    # Dados Profissionais
    SITUACAO_PROFISSIONAL_CHOICES = (('Desempregado', 'Desempregado'), ('Autonomo', 'Autônomo'), ('Empregado', 'Empregado'), ('Estudante', 'Estudante'), ('Auxilio', 'Auxílio'), ('INSS', 'INSS'), ('Aposentado', 'Aposentado'))
    situacao_profissional = models.CharField(max_length=20, choices=SITUACAO_PROFISSIONAL_CHOICES, blank=True, null=True, verbose_name="Situação Profissional")
    renda_individual = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Renda Individual")

    # Composição Familiar
    num_moradores = models.PositiveIntegerField(blank=True, null=True, verbose_name="Nº de Moradores")
    quantos_trabalham = models.PositiveIntegerField(blank=True, null=True, verbose_name="Quantos Trabalham")
    renda_moradores = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Renda dos Outros Moradores")

    @property
    def renda_familiar(self):
        renda_ind = self.renda_individual or 0
        renda_mor = self.renda_moradores or 0
        return renda_ind + renda_mor

    @property
    def renda_per_capita(self):
        if self.num_moradores and self.num_moradores > 0:
            return self.renda_familiar / self.num_moradores
        return self.renda_familiar

    @property
    def whatsapp_link(self):
        import re
        phone = self.whatsapp if self.whatsapp else self.telefone_principal
        if phone:
            # Remove tudo que não for dígito
            clean_number = re.sub(r'\D', '', phone)
            return f"55{clean_number}"
        return None

    # Inscrição
    COMO_SOUBE_CHOICES = (('Redes Sociais', 'Redes Sociais'), ('Site Prefeitura', 'Site Prefeitura'), ('Amigo', 'Amigo'), ('Panfleto', 'Panfleto'), ('Outros', 'Outros'))
    como_soube = models.CharField(max_length=50, choices=COMO_SOUBE_CHOICES, blank=True, null=True, verbose_name="Como soube do curso?")
    
    TURNO_CHOICES = (
        ('Manhã', 'Manhã'),
        ('Tarde', 'Tarde'),
        ('Noite', 'Noite'),
    )
    turno_interesse = models.CharField(max_length=100, blank=True, null=True, verbose_name="Turno de Interesse")
    
    receber_notificacoes = models.BooleanField(default=True, verbose_name="Deseja receber atualizações de cursos?")
    
    # Campos de controle
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    score_total = models.IntegerField(default=0, editable=False, verbose_name="Score Total")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações do Histórico")

    def save(self, *args, **kwargs):
        from core.utils import normalize_name, clean_digits
        if self.nome_completo:
            self.nome_completo = normalize_name(self.nome_completo)
        if self.cpf:
            self.cpf = clean_digits(self.cpf)
        # Limpar também telefones para consistência
        if self.whatsapp:
            self.whatsapp = clean_digits(self.whatsapp)
        if self.telefone_principal:
            self.telefone_principal = clean_digits(self.telefone_principal)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo

    @property
    def cpf_formatado(self):
        if self.cpf and len(self.cpf) == 11:
            return f"{self.cpf[:3]}.{self.cpf[3:6]}.{self.cpf[6:9]}-{self.cpf[9:]}"
        return self.cpf


class ArquivoAluno(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='arquivos', verbose_name="Aluno")
    arquivo = models.FileField(upload_to='documentos_alunos/%Y/%m/%d/', verbose_name="Arquivo")
    nome = models.CharField(max_length=255, verbose_name="Nome do Arquivo")
    data_upload = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    enviado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, verbose_name="Enviado por")

    class Meta:
        verbose_name = "Arquivo do Aluno"
        verbose_name_plural = "Arquivos dos Alunos"
        ordering = ['-data_upload']

    def __str__(self):
        return f"{self.nome} - {self.aluno.nome_completo}"

    @property
    def extensao(self):
        import os
        name, extension = os.path.splitext(self.arquivo.name)
        return extension.lower()

    @property
    def is_image(self):
        return self.extensao in ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    @property
    def is_pdf(self):
        return self.extensao == '.pdf'


class WebSocialMember(models.Model):
    aluno = models.OneToOneField(Aluno, on_delete=models.CASCADE, related_name='web_social_record', verbose_name="Aluno")
    ano_inclusao = models.PositiveIntegerField(verbose_name="Ano de Inclusão")
    data_inclusao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Inclusão")
    
    class Meta:
        verbose_name = "Membro Web Social"
        verbose_name_plural = "Membros Web Social"
        ordering = ['-data_inclusao']

    def __str__(self):
        return f"{self.aluno.nome_completo} ({self.ano_inclusao})"