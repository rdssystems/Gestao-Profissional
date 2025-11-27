from django.contrib import admin
from .models import Aluno

@admin.register(Aluno)
class AlunoAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'cpf', 'email_principal', 'escola', 'idade')
    search_fields = ('nome_completo', 'cpf', 'email_principal', 'escola__nome')
    list_filter = ('escola', 'sexo', 'estado_civil', 'situacao_profissional', 'escolaridade')
    readonly_fields = ('data_criacao', 'data_atualizacao', 'idade', 'renda_familiar', 'renda_per_capita')
    
    fieldsets = (
        ('Relacionamentos', {
            'fields': ('escola', 'cursos_interesse')
        }),
        ('Identificação', {
            'fields': ('nome_completo', 'cpf', 'rg', 'orgao_exp', 'data_emissao')
        }),
        ('Nascimento', {
            'fields': ('data_nascimento', 'idade')
        }),
        ('Informações Sociais', {
            'fields': ('sexo', 'estado_civil', 'cor_raca', 'nome_mae', 'naturalidade', 'uf_naturalidade', 'deficiencia', 'escolaridade')
        }),
        ('Contato', {
            'fields': ('email_principal', 'whatsapp', 'telefone_principal')
        }),
        ('Endereço', {
            'fields': ('endereco_cep', 'endereco_rua', 'endereco_numero', 'endereco_bairro', 'endereco_cidade', 'endereco_estado', 'tempo_moradia', 'tipo_moradia')
        }),
        ('Dados Profissionais', {
            'fields': ('situacao_profissional', 'renda_individual')
        }),
        ('Composição Familiar', {
            'fields': ('num_moradores', 'quantos_trabalham', 'renda_moradores', 'renda_familiar', 'renda_per_capita')
        }),
        ('Inscrição', {
            'fields': ('como_soube',)
        }),
        ('Datas de Controle', {
            'fields': ('data_criacao', 'data_atualizacao'),
            'classes': ('collapse',)
        }),
    )