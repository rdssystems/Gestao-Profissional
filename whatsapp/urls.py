from django.urls import path
from . import views

app_name = 'whatsapp'

urlpatterns = [
    # Global/Staff Default (Uses user profile school)
    path('', views.config_view, name='config'),
    path('criar-instancia/', views.create_instance_view, name='criar_instancia'),
    path('qr-code/', views.get_qr_code_view, name='qr_code'),
    path('status/', views.check_status_view, name='check_status'),
    path('desconectar/', views.disconnect_view, name='desconectar'),

    # Admin School-Specific (Requires superuser)
    path('<int:escola_id>/', views.config_view, name='config_escola'),
    path('<int:escola_id>/criar-instancia/', views.create_instance_view, name='criar_instancia_escola'),
    path('<int:escola_id>/qr-code/', views.get_qr_code_view, name='qr_code_escola'),
    path('<int:escola_id>/status/', views.check_status_view, name='check_status_escola'),
    path('<int:escola_id>/desconectar/', views.disconnect_view, name='desconectar_escola'),
]
