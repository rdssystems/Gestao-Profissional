from django.urls import path
from . import views

app_name = 'score_config'

urlpatterns = [
    path('configurar/', views.ConfiguracaoScoreView.as_view(), name='configurar'),
]
