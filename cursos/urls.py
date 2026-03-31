from django.urls import path
from . import views

app_name = 'cursos'

urlpatterns = [
    path('', views.CursoListView.as_view(), name='lista_cursos'),
    path('novo/', views.CursoCreateView.as_view(), name='criar_curso'),
    path('<int:pk>/', views.CursoDetailView.as_view(), name='detalhe_curso'),
    path('<int:pk>/editar/', views.CursoUpdateView.as_view(), name='editar_curso'),
    path('<int:pk>/excluir/', views.CursoDeleteView.as_view(), name='excluir_curso'),
    path('<int:pk>/concluintes/', views.CursoConcluintesView.as_view(), name='curso_concluintes'),
    path('<int:pk>/concluintes/xlsx/', views.CursoConcluintesXLSXView.as_view(), name='curso_concluintes_xlsx'),
    path('<int:pk>/imprimir-lista/', views.CursoImprimirListaView.as_view(), name='curso_imprimir_lista'),
    path('<int:pk>/alterar_status/', views.CursoStatusUpdateView.as_view(), name='alterar_status_curso'),

    # URLs para Parceiro
    path('parceiros/', views.ParceiroListView.as_view(), name='lista_parceiros'),
    path('parceiro/novo/', views.ParceiroCreateView.as_view(), name='criar_parceiro'),
    path('parceiro/<int:pk>/editar/', views.ParceiroUpdateView.as_view(), name='editar_parceiro'),
    path('parceiro/<int:pk>/excluir/', views.ParceiroDeleteView.as_view(), name='excluir_parceiro'),

    # URLs para TipoCurso
    path('tipos/', views.TipoCursoListView.as_view(), name='lista_tipos_curso'),
    path('tipos/novo/', views.TipoCursoCreateView.as_view(), name='criar_tipo_curso'),
    path('tipos/<int:pk>/editar/', views.TipoCursoUpdateView.as_view(), name='editar_tipo_curso'),
    path('tipos/<int:pk>/excluir/', views.TipoCursoDeleteView.as_view(), name='excluir_tipo_curso'),
    # URLs para Inscrição
    path('<int:curso_pk>/inscrever/', views.InscricaoCreateView.as_view(), name='inscrever_aluno'),
    path('inscricao/<int:pk>/alterar-status/', views.UpdateInscricaoStatusView.as_view(), name='alterar_status_inscricao'),
    path('inscricao/<int:pk>/excluir/', views.InscricaoDeleteView.as_view(), name='excluir_inscricao'),

    # URL para a nova página de Matrícula
    path('matriculas/', views.MatriculaView.as_view(), name='matricula'),
    path('matricular-direto/', views.MatricularAlunoDiretoView.as_view(), name='matricular_aluno_direto'),
    path('cancelar-matricula-direto/', views.CancelarMatriculaDiretoView.as_view(), name='cancelar_matricula_direto'),

    # URLs para Chamada
    path('chamadas/', views.ChamadaCursoListView.as_view(), name='lista_cursos_chamada'),
    path('chamadas/<int:curso_pk>/fazer/', views.FazerChamadaView.as_view(), name='fazer_chamada'),
    path('chamadas/<int:curso_pk>/fazer/<int:registro_aula_pk>/', views.FazerChamadaView.as_view(), name='fazer_chamada_editar'),
    path('chamadas/<int:curso_pk>/historico/', views.HistoricoChamadasCursoView.as_view(), name='listar_chamadas_curso'),
    path('chamadas/<int:curso_pk>/relatorio/', views.RelatorioFrequenciaView.as_view(), name='relatorio_frequencia'),

    # URL para upload de CSV de cursos
    path('upload-csv/', views.CursoCSVUploadView.as_view(), name='upload_cursos_csv'),
    path('download-template/', views.DownloadCursoTemplateView.as_view(), name='download_template_cursos'),

    # Chamada Pública (via Token)
    path('chamada-publica/<uuid:token>/', views.ChamadaPublicaView.as_view(), name='chamada_publica'),
    path('admin/fix-tokens/', views.RegenerarTokensView.as_view(), name='fix_tokens'),
]