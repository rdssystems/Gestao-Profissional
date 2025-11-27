from django.contrib import admin
from .models import Curso, Inscricao, TipoCurso, RegistroAula, Chamada # Importar novos modelos

@admin.register(TipoCurso)
class TipoCursoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'escola')
    search_fields = ('nome', 'escola__nome')
    list_filter = ('escola',)

class ChamadaInline(admin.TabularInline): # Usar TabularInline para uma exibição mais compacta
    model = Chamada
    extra = 0 # Não exibir formulários extras vazios por padrão
    # fields = ('inscricao', 'status_presenca',) # Opcional: especificar campos a exibir
    autocomplete_fields = ['inscricao'] # Ajuda a procurar inscrições se houver muitas

@admin.register(RegistroAula)
class RegistroAulaAdmin(admin.ModelAdmin):
    list_display = ('curso', 'data_aula', 'observacoes')
    search_fields = ('curso__nome', 'data_aula')
    list_filter = ('curso', 'data_aula')
    date_hierarchy = 'data_aula'
    inlines = [ChamadaInline] # Adicionar o inline para Chamada

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Se for um novo RegistroAula, pré-preenche as Chamadas com alunos inscritos
        if not obj: # Apenas para o formulário de criação (add)
            # A lógica para pré-popular será feita no momento da criação do RegistroAula
            # para garantir que apenas alunos ativos sejam adicionados.
            pass
        return form

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Se um novo RegistroAula foi criado, crie entradas de Chamada para todos os alunos inscritos
        if not change: # Se for uma nova instância
            inscricoes_do_curso = Inscricao.objects.filter(
                curso=obj.curso, 
                status='cursando' # Apenas alunos cursando devem estar na chamada
            )
            for inscricao in inscricoes_do_curso:
                Chamada.objects.get_or_create(
                    registro_aula=obj,
                    inscricao=inscricao,
                    defaults={'status_presenca': 'A'} # Padrão: Ausente
                )


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_curso', 'escola', 'carga_horaria', 'data_inicio', 'data_fim', 'status')
    search_fields = ('nome', 'tipo_curso__nome', 'escola__nome', 'status')
    list_filter = ('escola', 'tipo_curso', 'status', 'carga_horaria')
    date_hierarchy = 'data_inicio'

@admin.register(Inscricao)
class InscricaoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'curso', 'data_inscricao', 'status') # Adicionar status
    search_fields = ('aluno__nome_completo', 'curso__nome')
    list_filter = ('curso__escola', 'curso', 'status', 'data_inscricao') # Adicionar status ao filtro
    date_hierarchy = 'data_inscricao'
