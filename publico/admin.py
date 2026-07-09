from django.contrib import admin
from .models import BlocoConteudo


@admin.register(BlocoConteudo)
class BlocoConteudoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'tipo', 'escola', 'ativo', 'ordem')
    list_filter = ('tipo', 'ativo', 'escola')
    search_fields = ('titulo',)
