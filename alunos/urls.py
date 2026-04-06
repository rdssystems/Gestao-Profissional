from django.urls import path
from . import views

app_name = 'alunos'

urlpatterns = [
    path('', views.AlunoListView.as_view(), name='lista_alunos'),
    path('novo/', views.AlunoCreateView.as_view(), name='criar_aluno'),
    path('verificar-cpf/', views.AlunoVerificarCPFView.as_view(), name='verificar_cpf'),
    path('clonar-aluno/<int:pk>/', views.AlunoClonarView.as_view(), name='clonar_aluno'),
    path('<int:pk>/sucesso/', views.AlunoCadastroSucessoView.as_view(), name='cadastro_sucesso'),
    path('<int:pk>/', views.AlunoDetailView.as_view(), name='detalhe_aluno'),
    path('<int:pk>/editar/', views.AlunoUpdateView.as_view(), name='editar_aluno'),
    path('<int:pk>/excluir/', views.AlunoDeleteView.as_view(), name='excluir_aluno'),
    path('<int:pk>/historico/', views.AlunoHistoricoView.as_view(), name='historico_aluno'),
    path('<int:pk>/observacoes/', views.AlunoUpdateObservacoesView.as_view(), name='aluno_update_observacoes'),
    path('<int:pk>/cursos-interesse/', views.AlunoUpdateCursosInteresseView.as_view(), name='aluno_update_cursos_interesse'),
    path('<int:pk>/arquivos/upload/', views.AlunoArquivoAjaxUploadView.as_view(), name='aluno_arquivos_upload'),
    path('<int:pk>/arquivos/', views.AlunoArquivoActionView.as_view(), name='aluno_arquivos_lista'),
    path('<int:pk>/arquivos/<int:file_id>/excluir/', views.AlunoArquivoActionView.as_view(), name='aluno_arquivo_excluir'),
    path('upload-csv/', views.AlunoCSVUploadView.as_view(), name='upload_alunos_csv'),
    path('download-modelo-xlsx/', views.download_model_xlsx, name='download_modelo_aluno_xlsx'),
]
