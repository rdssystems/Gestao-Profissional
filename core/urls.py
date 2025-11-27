from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # path('', views.dashboard_view, name='dashboard'), # REMOVIDO
    path('agenda/', views.calendar_view, name='agenda'),
    path('api/events/', views.get_course_events, name='get_course_events'),
    path('sobre/', views.sobre_view, name='sobre'),
]
