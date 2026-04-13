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
    path('<int:pk>/qualitativos/', views.CursoQualitativosView.as_view(), name='curso_qualitativos'),

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

    # URLs para Ementa Padrão
    path('ementas/', views.EmentaPadraoListView.as_view(), name='lista_ementas'),
    path('ementas/novo/', views.EmentaPadraoCreateView.as_view(), name='criar_ementa'),
    path('ementas/<int:pk>/editar/', views.EmentaPadraoUpdateView.as_view(), name='editar_ementa'),
    path('ementas/<int:pk>/excluir/', views.EmentaPadraoDeleteView.as_view(), name='excluir_ementa'),
    path('ementas/<int:pk>/conteudo/', views.ObterEmentaView.as_view(), name='obter_ementa_conteudo'),

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
    path('chamadas/<int:curso_pk>/dados-data/', views.ObterDadosChamadaDataView.as_view(), name='obter_dados_chamada_data'),
    path('chamadas/registro/<int:pk>/excluir/', views.ExcluirRegistroAulaView.as_view(), name='excluir_registro_aula'),

    # URL para upload de CSV de cursos
    path('upload-csv/', views.CursoCSVUploadView.as_view(), name='upload_cursos_csv'),
    path('download-template/', views.DownloadCursoTemplateView.as_view(), name='download_template_cursos'),

    # Chamada Pública (via Token)
    path('chamada-publica/<uuid:token>/', views.ChamadaPublicaView.as_view(), name='chamada_publica'),
    path('admin/fix-tokens/', views.RegenerarTokensView.as_view(), name='fix_tokens'),

    # URLs para Avaliações
    path('<int:pk>/avaliacoes/', views.CursoAvaliacaoDashboardView.as_view(), name='dashboard_avaliacoes'),
    path('token/<uuid:token>/avaliar-professor-acesso/', views.AvaliarProfessorAcessoView.as_view(), name='avaliar_professor_acesso'),
    path('token/<uuid:token>/avaliar-professor-lista/', views.AvaliarProfessorListaView.as_view(), name='avaliacao_professor_lista'),
    path('token/<uuid:token>/avaliar-aluno/', views.AvaliarCursoPublicView.as_view(), name='avaliar_curso_publico'),
    path('avaliacao/aluno/<int:inscricao_pk>/ajax/', views.AvaliarEstudanteAjaxView.as_view(), name='avaliar_estudante_ajax'),
    path('avaliacao/detalhes/<int:inscricao_pk>/', views.AvaliacaoDetalhesView.as_view(), name='detalhes_avaliacao_ajax'),
    path('avaliacao/<int:pk>/consolidado/', views.CursoAvaliacaoConsolidadoView.as_view(), name='consolidado_avaliacoes'),
    path('avaliacao/<int:pk>/dados-graficos/', views.ObterDadosGraficosAvaliacaoView.as_view(), name='dados_graficos_avaliacao'),
]