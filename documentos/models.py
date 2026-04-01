import os
from django.db import models
from django.contrib.auth.models import User
from escolas.models import Escola

class Pasta(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True, related_name='pastas', verbose_name="Escola")
    nome = models.CharField(max_length=150, verbose_name="Nome da Pasta")
    pasta_pai = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subpastas', verbose_name="Pasta Pai")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")

    class Meta:
        verbose_name = "Pasta"
        verbose_name_plural = "Pastas"
        ordering = ['nome']
        unique_together = ['escola', 'nome', 'pasta_pai']

    def __str__(self):
        escola_nome = self.escola.nome if self.escola else "Global / Todas"
        return f"{self.nome} ({escola_nome})"

    def get_caminho(self):
        """Retorna uma lista com o caminho das pastas desde a raiz até esta pasta."""
        caminho = []
        atual = self
        while atual is not None:
            caminho.insert(0, atual)
            atual = atual.pasta_pai
        return caminho

class DocumentoUnidade(models.Model):
    CATEGORIA_CHOICES = (
        ('pedagogico', 'Pedagógico'),
        ('administrativo', 'Administrativo'),
        ('financeiro', 'Financeiro'),
        ('outros', 'Outros'),
    )

    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True, related_name='documentos')
    pasta = models.ForeignKey(Pasta, on_delete=models.CASCADE, null=True, blank=True, related_name='documentos', verbose_name="Pasta")
    nome = models.CharField(max_length=255, verbose_name="Nome do Arquivo")
    arquivo = models.FileField(upload_to='documentos_escola/%Y/%m/%d/', verbose_name="Arquivo")
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='outros', verbose_name="Categoria")
    data_upload = models.DateTimeField(auto_now_add=True, verbose_name="Data de Upload")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Enviado por")
    
    # Metadados automáticos
    tamanho = models.BigIntegerField(null=True, blank=True, verbose_name="Tamanho (bytes)")
    extensao = models.CharField(max_length=10, blank=True, verbose_name="Extensão")

    class Meta:
        verbose_name = "Documento da Unidade"
        verbose_name_plural = "Documentos da Unidade"
        ordering = ['-data_upload']

    def __str__(self):
        escola_nome = self.escola.nome if self.escola else "Global / Todas"
        return f"{self.nome} ({escola_nome})"

    def save(self, *args, **kwargs):
        if self.arquivo:
            # Extrair extensão e tamanho se for novo
            if not self.pk:
                self.tamanho = self.arquivo.size
                self.extensao = os.path.splitext(self.arquivo.name)[1].lower().replace('.', '')
                if not self.nome:
                    self.nome = self.arquivo.name
        super().save(*args, **kwargs)

    @property
    def is_image(self):
        return self.extensao in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    @property
    def is_pdf(self):
        return self.extensao == 'pdf'
    
    @property
    def icon_class(self):
        """Retorna o ícone do Bootstrap Icons baseado na extensão"""
        if self.is_image: return "bi-file-earmark-image text-success"
        if self.is_pdf: return "bi-file-earmark-pdf text-danger"
        if self.extensao in ['doc', 'docx']: return "bi-file-earmark-word text-primary"
        if self.extensao in ['xls', 'xlsx', 'csv']: return "bi-file-earmark-spreadsheet text-success"
        if self.extensao in ['ppt', 'pptx']: return "bi-file-earmark-slides text-warning"
        if self.extensao in ['zip', 'rar', '7z']: return "bi-file-earmark-zip text-secondary"
        return "bi-file-earmark-text text-muted"
