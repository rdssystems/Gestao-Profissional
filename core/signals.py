from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile, AuditLog
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Cria um perfil para um novo usuário ou apenas salva o perfil existente.
    """
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

@receiver(post_save, sender=AuditLog)
def broadcast_audit_log(sender, instance, created, **kwargs):
    """
    Envia uma notificação via WebSocket sempre que um Log de Auditoria é criado.
    Isso cobre Criação, Edição e Exclusão de objetos auditados.
    """
    if created:
        channel_layer = get_channel_layer()
        
        # Formata a mensagem
        user_name = instance.usuario.username if instance.usuario else "Sistema"
        action_display = instance.get_acao_display()
        obj_repr = str(instance.content_object) if instance.content_object else "Objeto desconhecido"
        
        msg_text = f"<strong>{user_name}</strong> realizou <strong>{action_display}</strong> em {obj_repr}"

        async_to_sync(channel_layer.group_send)(
            "global_notifications",
            {
                "type": "send_notification",
                "message": msg_text,
                "notification_type": "info"
            }
        )
