from django.urls import path
from . import views

app_name = 'documentos'

urlpatterns = [
    path('', views.DocumentoListView.as_view(), name='lista_documentos'),
    path('novo/', views.DocumentoUploadView.as_view(), name='documento_upload'),
    path('<int:pk>/excluir/', views.DocumentoDeleteView.as_view(), name='documento_excluir'),
    # Pastas
    path('pasta/nova/', views.PastaCreateView.as_view(), name='pasta_nova'),
    path('pasta/<int:pk>/excluir/', views.PastaDeleteView.as_view(), name='pasta_excluir'),
    # Ajx Upload
    path('upload-ajax/', views.DocumentoAjaxUploadView.as_view(), name='documento_upload_ajax'),
]
