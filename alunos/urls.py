from django.urls import path
from . import views

app_name = 'alunos'

urlpatterns = [
    path('', views.AlunoListView.as_view(), name='lista_alunos'),
    path('novo/', views.AlunoCreateView.as_view(), name='criar_aluno'),
    path('<int:pk>/sucesso/', views.AlunoCadastroSucessoView.as_view(), name='cadastro_sucesso'),
    path('<int:pk>/', views.AlunoDetailView.as_view(), name='detalhe_aluno'),
    path('<int:pk>/editar/', views.AlunoUpdateView.as_view(), name='editar_aluno'),
    path('<int:pk>/excluir/', views.AlunoDeleteView.as_view(), name='excluir_aluno'),
    path('<int:pk>/historico/', views.AlunoHistoricoView.as_view(), name='historico_aluno'),
    path('upload-csv/', views.AlunoCSVUploadView.as_view(), name='upload_alunos_csv'),
    path('download-modelo-xlsx/', views.download_model_xlsx, name='download_modelo_aluno_xlsx'),
]
