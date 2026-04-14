from django.contrib import admin
from .models import VideoTreinamento, ProgressoTreinamento

@admin.register(VideoTreinamento)
class VideoTreinamentoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'ordem', 'ativo', 'data_criacao')
    list_filter = ('ativo',)
    search_fields = ('titulo', 'descricao')
    ordering = ('ordem',)

@admin.register(ProgressoTreinamento)
class ProgressoTreinamentoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'video', 'concluido', 'data_conclusao')
    list_filter = ('concluido', 'usuario', 'video')
    search_fields = ('usuario__username', 'video__titulo')
