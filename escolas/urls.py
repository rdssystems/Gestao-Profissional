from django.urls import path
from . import views

app_name = 'escolas'

urlpatterns = [
    path('lista/', views.EscolaListView.as_view(), name='lista_escolas'), # Novo path para listar escolas
    path('', views.DashboardView.as_view(), name='dashboard'), # Dashboard agora em /escolas/ (root)
    path('nova/', views.EscolaCreateView.as_view(), name='criar_escola'),
    path('<int:pk>/', views.EscolaDetailView.as_view(), name='detalhe_escola'),
    path('<int:pk>/editar/', views.EscolaUpdateView.as_view(), name='editar_escola'),
    path('<int:pk>/excluir/', views.EscolaDeleteView.as_view(), name='excluir_escola'),
    path('<int:escola_id>/cursos/', views.CursosPorEscolaListView.as_view(), name='cursos_da_escola'),
    path('<int:escola_id>/alunos/', views.AlunosPorEscolaListView.as_view(), name='alunos_da_escola'),
    path('concluintes-global/', views.ConcluintesGlobalView.as_view(), name='concluintes_global'),
]
