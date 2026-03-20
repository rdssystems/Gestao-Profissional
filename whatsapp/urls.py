from django.urls import path
from . import views

app_name = 'whatsapp'

urlpatterns = [
    path('', views.config_view, name='config'),
    path('criar-instancia/', views.create_instance_view, name='criar_instancia'),
    path('qr-code/', views.get_qr_code_view, name='qr_code'),
    path('status/', views.check_status_view, name='check_status'),
    path('desconectar/', views.disconnect_view, name='desconectar'),
]
