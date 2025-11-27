from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.UserListView.as_view(), name='lista_usuarios'),
    path('novo/', views.UserCreateView.as_view(), name='criar_usuario'),
    path('<int:pk>/editar/', views.UserUpdateView.as_view(), name='editar_usuario'),
    path('<int:pk>/excluir/', views.UserDeleteView.as_view(), name='excluir_usuario'),
]

