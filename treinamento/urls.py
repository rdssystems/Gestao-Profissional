from django.urls import path
from . import views

app_name = 'treinamento'

urlpatterns = [
    path('', views.TreinamentoListView.as_view(), name='lista'),
    path('video/<int:pk>/', views.TreinamentoDetailView.as_view(), name='detalhe'),
    path('marcar-concluido/<int:pk>/', views.MarcarConcluidoAjaxView.as_view(), name='marcar_concluido'),
    path('relatorio/', views.RelatorioTreinamentoView.as_view(), name='relatorio'),
]
