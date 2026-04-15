from django.urls import re_path
from . import consumers
from cursos import consumers as cursos_consumers

websocket_urlpatterns = [
    re_path(r'ws/test/$', consumers.TestConsumer.as_asgi()),
    re_path(r'ws/cursos/$', cursos_consumers.CursosConsumer.as_asgi()),
]
