from django.urls import path
from . import views
from .views import AuditLogListView

app_name = 'core'

urlpatterns = [
    # path('', views.dashboard_view, name='dashboard'), 
    path('agenda/', views.calendar_view, name='agenda'),
    path('agenda/limpar/', views.limpar_agenda_cursos_view, name='limpar_agenda_cursos'),
    path('api/events/', views.get_course_events, name='get_course_events'),
    path('sobre/', views.sobre_view, name='sobre'),
    path('auditoria/', AuditLogListView.as_view(), name='lista_auditoria'),
    
    # Sistema de Avisos / Updates
    path('avisos/lido/<int:aviso_pk>/', views.marcar_aviso_lido, name='marcar_aviso_lido'),
    path('admin/avisos/', views.gerenciar_avisos, name='gerenciar_avisos'),
    path('admin/ativar-dev/', views.ativar_dev_view, name='ativar_dev'),
]
