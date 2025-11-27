from django.urls import path
from . import views

app_name = 'cursos'

urlpatterns = [
    path('', views.CursoListView.as_view(), name='lista_cursos'),
    path('novo/', views.CursoCreateView.as_view(), name='criar_curso'),
    path('<int:pk>/', views.CursoDetailView.as_view(), name='detalhe_curso'),
    path('<int:pk>/editar/', views.CursoUpdateView.as_view(), name='editar_curso'),
    path('<int:pk>/excluir/', views.CursoDeleteView.as_view(), name='excluir_curso'),
    path('<int:pk>/alterar_status/', views.CursoStatusUpdateView.as_view(), name='alterar_status_curso'),

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

    # URLs para Chamada
    path('chamadas/', views.ChamadaCursoListView.as_view(), name='lista_cursos_chamada'),
    path('chamadas/<int:curso_pk>/fazer/', views.FazerChamadaView.as_view(), name='fazer_chamada'),
    path('chamadas/<int:curso_pk>/fazer/<int:registro_aula_pk>/', views.FazerChamadaView.as_view(), name='fazer_chamada_editar'),
    path('chamadas/<int:curso_pk>/historico/', views.HistoricoChamadasCursoView.as_view(), name='listar_chamadas_curso'),

    # URL para upload de CSV de cursos
    path('upload-csv/', views.CursoCSVUploadView.as_view(), name='upload_cursos_csv'),
]