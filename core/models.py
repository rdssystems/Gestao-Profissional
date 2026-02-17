from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from escolas.models import Escola

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')

    def __str__(self):
        return f'Perfil de {self.user.username}'

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