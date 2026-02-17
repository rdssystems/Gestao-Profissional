from django.urls import path
from . import views
from .views import AuditLogListView

app_name = 'core'

urlpatterns = [
    # path('', views.dashboard_view, name='dashboard'), # REMOVIDO
    path('agenda/', views.calendar_view, name='agenda'),
    path('agenda/limpar/', views.limpar_agenda_cursos_view, name='limpar_agenda_cursos'), # Nova URL
    path('api/events/', views.get_course_events, name='get_course_events'),
    path('sobre/', views.sobre_view, name='sobre'),
    path('auditoria/', AuditLogListView.as_view(), name='lista_auditoria'),
]
