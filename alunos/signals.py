from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Aluno, WebSocialMember
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

@receiver(post_save, sender='cursos.Inscricao')
def incluir_aluno_web_social(sender, instance, created, **kwargs):
    """
    Inclui o aluno na Web Social quando sua matrícula é marcada como 'concluido'.
    Somente uma vez por aluno.
    """
    if instance.status == 'concluido':
        aluno = instance.aluno
        # Verificar se o aluno já está na Web Social
        if not WebSocialMember.objects.filter(aluno=aluno).exists():
            WebSocialMember.objects.create(
                aluno=aluno,
                ano_inclusao=timezone.now().year
            )

