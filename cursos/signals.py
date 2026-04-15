from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import RegistroAula, Chamada
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import date
from django.db.models import Q

def send_course_update(curso_id):
    channel_layer = get_channel_layer()
    hoje = date.today()
    
    # Recalcular indicadores para o real-time
    has_chamada_hoje = RegistroAula.objects.filter(curso_id=curso_id, data_aula=hoje).exists()
    
    has_pendencia_qualitativa = False
    if has_chamada_hoje:
        has_pendencia_qualitativa = Chamada.objects.filter(
            registro_aula__curso_id=curso_id,
            registro_aula__data_aula=hoje,
            status_presenca__in=['A', 'J']
        ).filter(
            Q(motivo_falta__isnull=True) | Q(motivo_falta='')
        ).exists()

    async_to_sync(channel_layer.group_send)(
        "cursos_updates",
        {
            "type": "status_update",
            "curso_id": curso_id,
            "has_chamada_hoje": has_chamada_hoje,
            "has_pendencia_qualitativa": has_pendencia_qualitativa,
        }
    )

@receiver(post_save, sender=RegistroAula)
@receiver(post_delete, sender=RegistroAula)
def registro_aula_changed(sender, instance, **kwargs):
    send_course_update(instance.curso_id)

@receiver(post_save, sender=Chamada)
@receiver(post_delete, sender=Chamada)
def chamada_changed(sender, instance, **kwargs):
    # Chamada -> RegistroAula -> Curso
    send_course_update(instance.registro_aula.curso_id)
