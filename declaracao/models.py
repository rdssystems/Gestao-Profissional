from django.db import models
from django.conf import settings
from cursos.models import Inscricao
import uuid

class Declaracao(models.Model):
    STATUS_CHOICES = (
        ('concluido', 'Concluído'),
        ('matriculado', 'Matriculado'),
        ('cursando', 'Cursando'),
    )

    inscricao = models.ForeignKey(Inscricao, on_delete=models.CASCADE, related_name='declaracoes')
    emitido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='declaracoes_emitidas')
    
    # Este texto é gerado por uma função utilitária e passado durante a criação
    texto = models.TextField(editable=False)
    
    # Armazena o status que foi usado para esta declaração
    status_aplicado = models.CharField(max_length=20, choices=STATUS_CHOICES, editable=False)
    
    assinatura_digital = models.TextField(blank=True, null=True, help_text="Armazena a assinatura em formato Base64")
    data_emissao = models.DateTimeField(auto_now_add=True, editable=False)
    
    # Um código único para validação
    hash_validacao = models.CharField(max_length=64, unique=True, blank=True, help_text="Hash para validar a autenticidade do documento")

    def __str__(self):
        return f"Declaração ({self.get_status_aplicado_display()}) para {self.inscricao.aluno.nome_completo} - Curso: {self.inscricao.curso.nome}"

    def save(self, *args, **kwargs):
        if not self.hash_validacao:
            self.hash_validacao = uuid.uuid4().hex
        super().save(*args, **kwargs)
