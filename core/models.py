from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from escolas.models import Escola

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')
    is_developer = models.BooleanField(default=False, verbose_name="Desenvolvedor (Acesso a Updates)")

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