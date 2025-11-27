from django.contrib import admin
from .models import Escola

@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'telefone')
    search_fields = ('nome', 'email')
    # Adicionando filtros para nome e email
    list_filter = ('nome', 'email')