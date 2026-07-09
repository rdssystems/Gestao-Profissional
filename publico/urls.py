from django.urls import path
from . import views

app_name = 'publico'

urlpatterns = [
    # Gestao (vem antes do slug para nao conflitar)
    path('config/', views.PublicoConfigView.as_view(), name='config'),
    path('config/<int:escola_id>/blocos/', views.BlocoListView.as_view(), name='bloco_list'),
    path('config/<int:escola_id>/blocos/novo/', views.BlocoCreateView.as_view(), name='bloco_create'),
    path('config/bloco/<int:pk>/editar/', views.BlocoUpdateView.as_view(), name='bloco_update'),
    path('config/bloco/<int:pk>/excluir/', views.BlocoDeleteView.as_view(), name='bloco_delete'),

    # Gestão de Cursos e Ementas Globais
    path('config/ementas/', views.CursoEmentaListView.as_view(), name='ementa_list'),
    path('config/ementas/novo/', views.CursoEmentaCreateView.as_view(), name='ementa_create'),
    path('config/ementas/<int:pk>/editar/', views.CursoEmentaUpdateView.as_view(), name='ementa_update'),
    path('config/ementas/<int:pk>/excluir/', views.CursoEmentaDeleteView.as_view(), name='ementa_delete'),

    # Publicas
    path('', views.PublicoHomeView.as_view(), name='home'),
    path('<slug:slug>/', views.PublicoEscolaView.as_view(), name='escola'),
    path('<slug:slug>/cadastro/', views.PublicoCadastroView.as_view(), name='cadastro'),
]
