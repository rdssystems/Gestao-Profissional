from django.db import models
from django.contrib.auth.models import User

class Escola(models.Model):
    nome = models.CharField(max_length=200)
    endereco = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20)
    coordenador_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escola_coordenada')

    def __str__(self):
        return self.nome