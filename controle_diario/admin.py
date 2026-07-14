from django.contrib import admin
from .models import ControleDiario, RelatorioDiarioSine

@admin.register(ControleDiario)
class ControleDiarioAdmin(admin.ModelAdmin):
    list_display = ('escola', 'data', 'atendimento', 'inscricoes', 'pessoas_presentes', 'usuario')
    list_filter = ('data', 'escola')
    search_fields = ('escola__nome', 'usuario__username')

@admin.register(RelatorioDiarioSine)
class RelatorioDiarioSineAdmin(admin.ModelAdmin):
    list_display = ('data', 'total_procedimentos', 'usuario')
    list_filter = ('data',)
    search_fields = ('usuario__username',)
