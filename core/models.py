from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from escolas.models import Escola

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    is_developer = models.BooleanField(default=False, verbose_name="Desenvolvedor (Acesso a Updates)")
    
    NIVEL_ACESSO_CHOICES = (
        ('ADMIN_CP', 'Administrador de CPs'),
        ('ADMIN_UDITECH', 'Administrador de Uditechs'),
        ('SUPERUSER', 'Superusuário Global'),
    )

    nivel_acesso = models.CharField(
        max_length=20,
        choices=NIVEL_ACESSO_CHOICES,
        default='ADMIN_CP',
        verbose_name="Nível de Acesso Administrativo"
    )

    @property
    def is_admin_uditech(self):
        return self.nivel_acesso == 'ADMIN_UDITECH'

    @property
    def is_admin_cp(self):
        return self.nivel_acesso == 'ADMIN_CP'


    def __str__(self):
        return f'Perfil de {self.user.username}'

class Aviso(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título")
    conteudo = models.TextField(verbose_name="Conteúdo da Atualização")
    data_postagem = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    visualizado_por = models.ManyToManyField(User, blank=True, related_name='avisos_lidos')

    class Meta:
        ordering = ['-data_postagem']
        verbose_name = 'Aviso / Atualização'
        verbose_name_plural = 'Avisos / Atualizações'

    def __str__(self):
        return self.titulo

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Criação'),
        ('UPDATE', 'Edição'),
        ('DELETE', 'Exclusão'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    )

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    acao = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # Campos para ligar a qualquer tabela (Aluno, Curso, Escola, etc)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    detalhes = models.TextField(blank=True, null=True, help_text="JSON ou texto descrevendo a mudança")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Log de Auditoria'
        verbose_name_plural = 'Logs de Auditoria'

    def __str__(self):
        return f"{self.usuario} - {self.acao} - {self.data_hora}"

    @property
    def notification_text(self):
        return self.get_notification_text()

    def get_notification_text(self):
        if not self.content_type:
            return f"{self.usuario.get_full_name() or self.usuario.username} realizou uma ação."
            
        model_name = self.content_type.model
        usuario_nome = self.usuario.get_full_name() or self.usuario.username if self.usuario else "Sistema"
        
        try:
            if self.detalhes == "Qualitativo enviado para a Turma":
                obj = self.content_object
                curso_nome = obj.nome if obj else "Desconhecido"
                return f"<strong>{usuario_nome}</strong> lançou qualitativos do curso <strong>{curso_nome}</strong>"
                
            if model_name == 'registroaula':
                obj = self.content_object
                curso_nome = obj.curso.nome if obj and obj.curso else "Desconhecido"
                return f"<strong>{usuario_nome}</strong> enviou a lista de chamadas do curso <strong>{curso_nome}</strong>"
                
            elif model_name == 'avaliacaoprofessoraluno':
                obj = self.content_object
                if obj and obj.inscricao:
                    aluno_nome = obj.inscricao.aluno.nome_completo
                    curso_nome = obj.inscricao.curso.nome
                    return f"<strong>{obj.professor_nome or usuario_nome}</strong> avaliou o aluno <strong>{aluno_nome}</strong> no curso <strong>{curso_nome}</strong>"
                return f"<strong>{usuario_nome}</strong> preencheu uma avaliação de aluno"
                
            elif model_name == 'avaliacaoalunocurso':
                obj = self.content_object
                curso_nome = obj.inscricao.curso.nome if obj and obj.inscricao else "Desconhecido"
                return f"<strong>{usuario_nome}</strong> preencheu a avaliação do curso <strong>{curso_nome}</strong>"
                
            elif model_name == 'arquivoaluno':
                obj = self.content_object
                aluno_nome = obj.aluno.nome_completo if obj and obj.aluno else "Desconhecido"
                return f"<strong>{usuario_nome}</strong> atualizou um arquivo na ficha do aluno <strong>{aluno_nome}</strong>"
                
        except Exception:
            pass
            
        acao_str = self.get_acao_display().lower()
        tabela = self.content_type.name.title()
        nome_objeto = ""
        if self.content_object:
            nome_objeto = f" ({str(self.content_object)[:30]})"
        return f"<strong>{usuario_nome}</strong> {acao_str} um registro em <strong>{tabela}</strong>{nome_objeto}"


class EmailDestinatario(models.Model):
    """Destinatários cadastrados para receber o relatório do Controle Diário"""
    nome = models.CharField(max_length=100, verbose_name="Nome")
    email = models.EmailField(unique=True, verbose_name="E-mail")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    adicionado_em = models.DateTimeField(auto_now_add=True)
    adicionado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Adicionado por"
    )

    class Meta:
        ordering = ['nome']
        verbose_name = "Destinatário de E-mail"
        verbose_name_plural = "Destinatários de E-mail"

    def __str__(self):
        return f"{self.nome} <{self.email}>"


class AgendamentoEmail(models.Model):
    """
    Configuração de agendamento para o envio do relatório do Controle Diário.
    Modelo Singleton — deve existir apenas 1 registro no banco.
    """
    # Dias da semana como campos booleanos individuais (mais fácil de consultar)
    segunda = models.BooleanField(default=True, verbose_name="Segunda-feira")
    terca = models.BooleanField(default=True, verbose_name="Terça-feira")
    quarta = models.BooleanField(default=True, verbose_name="Quarta-feira")
    quinta = models.BooleanField(default=True, verbose_name="Quinta-feira")
    sexta = models.BooleanField(default=True, verbose_name="Sexta-feira")
    sabado = models.BooleanField(default=False, verbose_name="Sábado")
    domingo = models.BooleanField(default=False, verbose_name="Domingo")

    horario_envio = models.TimeField(default='18:00', verbose_name="Horário de Envio")
    ativo = models.BooleanField(default=True, verbose_name="Envio Automático Ativo")

    atualizado_em = models.DateTimeField(auto_now=True)
    atualizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Atualizado por"
    )

    class Meta:
        verbose_name = "Agendamento de E-mail"
        verbose_name_plural = "Agendamento de E-mail"

    def __str__(self):
        return f"Agendamento: {self.horario_envio.strftime('%H:%M')}"

    @classmethod
    def get_config(cls):
        """Retorna a configuração existente ou cria uma com valores padrão."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def deve_enviar_agora(self):
        """
        Verifica se o envio deve ocorrer agora com base no dia e hora configurados.
        Janela de 59 minutos a partir do horário configurado, com suporte a
        horários que cruzam a meia-noite (ex: 23:55 -> janela vai ate 00:54).
        """
        if not self.ativo:
            return False

        from django.utils import timezone
        from datetime import timedelta

        DIAS = {
            0: self.segunda,
            1: self.terca,
            2: self.quarta,
            3: self.quinta,
            4: self.sexta,
            5: self.sabado,
            6: self.domingo,
        }

        agora = timezone.localtime(timezone.now()).replace(second=0, microsecond=0)

        # Janela de hoje: horario_envio → horario_envio + 59min
        inicio_hoje = agora.replace(
            hour=self.horario_envio.hour,
            minute=self.horario_envio.minute,
            second=0,
            microsecond=0
        )
        fim_hoje = inicio_hoje + timedelta(minutes=59)
        if inicio_hoje <= agora <= fim_hoje:
            return DIAS.get(inicio_hoje.weekday(), False)

        # Janela de ontem (cobre cruzamento de meia-noite, ex: config 23:55 → envia até 00:54)
        inicio_ontem = inicio_hoje - timedelta(days=1)
        fim_ontem = inicio_ontem + timedelta(minutes=59)
        if inicio_ontem <= agora <= fim_ontem:
            return DIAS.get(inicio_ontem.weekday(), False)

        return False

    @property
    def dias_ativos_display(self):
        nomes = []
        if self.segunda: nomes.append("Seg")
        if self.terca:   nomes.append("Ter")
        if self.quarta:  nomes.append("Qua")
        if self.quinta:  nomes.append("Qui")
        if self.sexta:   nomes.append("Sex")
        if self.sabado:  nomes.append("Sáb")
        if self.domingo: nomes.append("Dom")
        return ", ".join(nomes) if nomes else "Nenhum dia"