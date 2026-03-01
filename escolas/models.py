from django.db import models
from django.contrib.auth.models import User

class Escola(models.Model):
    nome = models.CharField(max_length=200)
    endereco = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20)
    coordenador_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escola_coordenada')
    data_atualizacao = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.nome

    def get_telefone_formatado(self):
        # Remove todos os caracteres não numéricos
        if not self.telefone:
            return ""
        
        apenas_numeros = ''.join(filter(str.isdigit, self.telefone))

        # Aplica a máscara (99) 9999-9999 ou (99) 99999-9999
        if len(apenas_numeros) == 10: # (DD) NNNN-NNNN
            return f"({apenas_numeros[0:2]}) {apenas_numeros[2:6]}-{apenas_numeros[6:10]}"
        elif len(apenas_numeros) == 11: # (DD) NNNNN-NNNN
            return f"({apenas_numeros[0:2]}) {apenas_numeros[2:7]}-{apenas_numeros[7:11]}"
        else:
            # Se não se encaixa nos padrões, retorna o número original ou uma mensagem de erro
            return self.telefone # Ou poderia ser "Número inválido"