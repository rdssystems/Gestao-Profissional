from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('contas/', include('django.contrib.auth.urls')),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('escolas/', include('escolas.urls', namespace='escolas')),
    path('cursos/', include('cursos.urls', namespace='cursos')),
    path('alunos/', include('alunos.urls', namespace='alunos')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    path('score/', include('score_config.urls', namespace='score_config')),

    # Re-incluindo core.urls para que o namespace 'core' e a URL 'core:agenda' sejam registrados
    path('agenda/', include('core.urls', namespace='core')), # ADICIONADO AQUI
    path('', include('escolas.urls')), # Novo root para o dashboard da escola
]