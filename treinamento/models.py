from django.db import models
from django.contrib.auth.models import User

class VideoTreinamento(models.Model):
    titulo = models.CharField(max_length=200, verbose_name="Título da Aula")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição / O que aprender")
    youtube_url = models.URLField(verbose_name="URL do Vídeo (YouTube)")
    ordem = models.PositiveIntegerField(default=0, verbose_name="Ordem de Exibição")
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Vídeo de Treinamento"
        verbose_name_plural = "Vídeos de Treinamento"
        ordering = ['ordem', 'data_criacao']

    def __str__(self):
        return self.titulo

    @property
    def youtube_id(self):
        """Extrai o ID do vídeo do YouTube a partir da URL."""
        import re
        pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
        match = re.search(pattern, self.youtube_url)
        return match.group(1) if match else None

class ProgressoTreinamento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progressos_treinamento')
    video = models.ForeignKey(VideoTreinamento, on_delete=models.CASCADE, related_name='visualizacoes')
    concluido = models.BooleanField(default=False, verbose_name="Concluído")
    data_conclusao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Progresso de Treinamento"
        verbose_name_plural = "Progressos de Treinamento"
        unique_together = ('usuario', 'video')

    def __str__(self):
        return f"{self.usuario.username} - {self.video.titulo} ({'Concluído' if self.concluido else 'Pendente'})"
