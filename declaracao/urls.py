from django.urls import path, re_path
from . import views

app_name = 'declaracao'

urlpatterns = [
    path('buscar/', views.buscar_aluno_view, name='buscar_aluno'),
    path('aluno/<int:aluno_id>/cursos/', views.listar_cursos_view, name='listar_cursos_aluno'),
    
    # Original path for generating declaration
    path('gerar/<int:inscricao_id>/', views.gerar_declaracao_view, name='gerar_declaracao'),
    
    # New path for generating declaration with an optional declaration_type
    re_path(r'^gerar/(?P<inscricao_id>\d+)/(?:(?P<declaration_type>matriculado|cursando)/)?$', views.gerar_declaracao_view, name='gerar_declaracao_com_tipo'),

    path('salvar/<int:inscricao_id>/', views.salvar_declaracao_view, name='salvar_declaracao'),
    path('sucesso/<int:declaracao_id>/', views.declaracao_sucesso_view, name='declaracao_sucesso'),
    path('imprimir/<str:hash_validacao>/', views.imprimir_declaracao_view, name='imprimir_declaracao'),
]
