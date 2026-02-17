from django.urls import path
from . import views

app_name = 'controle_diario'

urlpatterns = [
    path('preencher/', views.preencher_controle_diario_view, name='preencher'),
    path('admin-view/', views.controle_diario_admin_view, name='admin_view'), # Nova URL
]
