from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from escolas import views as escolas_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contas/', include('django.contrib.auth.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('escolas/', include('escolas.urls', namespace='escolas')),
    path('cursos/', include('cursos.urls', namespace='cursos')),
    path('alunos/', include('alunos.urls', namespace='alunos')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('score/', include('score_config.urls', namespace='score_config')),
    path('declaracoes/', include('declaracao.urls', namespace='declaracao')),
    path('controle-diario/', include('controle_diario.urls', namespace='controle_diario')),
    path('whatsapp/', include('whatsapp.urls', namespace='whatsapp')),

    path('core/', include('core.urls', namespace='core')),
    path('', escolas_views.DashboardView.as_view(), name='dashboard_root'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
