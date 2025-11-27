from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Aluno
from .score import calcular_score_aluno

@receiver(post_save, sender=Aluno)
def atualizar_score_aluno(sender, instance, created, **kwargs):
    """
    Atualiza o score do aluno sempre que um objeto Aluno é salvo.
    """
    # Calcula o novo score
    novo_score = calcular_score_aluno(instance)

    # Atualiza o campo score_total sem disparar o sinal novamente
    # para evitar um loop infinito.
    if instance.score_total != novo_score:
        Aluno.objects.filter(pk=instance.pk).update(score_total=novo_score)
