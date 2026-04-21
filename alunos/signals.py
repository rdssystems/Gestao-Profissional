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
    Inclui o aluno na Web Social quando sua matrícula é marcada como 'concluido'
    ou quando for 'desistente' com pelo menos 1 presença.
    Garante somente 1 registro por CPF.
    """
    if instance.status == 'concluido' or (instance.status == 'desistente' and instance.chamadas.filter(status_presenca='P').exists()):
        aluno = instance.aluno
        # Verificar se algum aluno com o mesmo CPF já está na Web Social para garantir 1 por CPF
        if not WebSocialMember.objects.filter(aluno__cpf=aluno.cpf).exists():
            WebSocialMember.objects.create(
                aluno=aluno,
                ano_inclusao=timezone.now().year
            )

