from django.db import models
from django.contrib.auth.models import User
from escolas.models import Escola

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles')

    def __str__(self):
        return f'Perfil de {self.user.username}'