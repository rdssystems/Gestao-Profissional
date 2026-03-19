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
    Agora segmentado por escola.
    """
    if created:
        channel_layer = get_channel_layer()
        
        # Determina o grupo de destino
        group_name = "global_notifications"
        
        # Tenta identificar a escola do objeto alterado
        obj = instance.content_object
        escola_id = None
        
        if obj:
            # 1. Se o objeto tem escola_id diretamente (Escola, Aluno, Curso, TipoCurso)
            if hasattr(obj, 'escola_id') and obj.escola_id:
                escola_id = obj.escola_id
            # 2. Se for Inscricao ou RegistroAula (tem .curso)
            elif hasattr(obj, 'curso') and hasattr(obj.curso, 'escola_id'):
                escola_id = obj.curso.escola_id
            # 3. Se for Chamada ou similar (tem .inscricao ou .aluno)
            elif hasattr(obj, 'inscricao') and hasattr(obj.inscricao.curso, 'escola_id'):
                escola_id = obj.inscricao.curso.escola_id
            elif hasattr(obj, 'aluno') and hasattr(obj.aluno, 'escola_id'):
                escola_id = obj.aluno.escola_id
            # 4. Se for Declaracao (tem .aluno)
            elif hasattr(obj, 'aluno') and hasattr(obj.aluno, 'escola_id'):
                escola_id = obj.aluno.escola_id

        # Se não achou pelo objeto, tenta pelo usuário que fez a ação
        if not escola_id and instance.usuario and hasattr(instance.usuario, 'profile') and instance.usuario.profile.escola:
            escola_id = instance.usuario.profile.escola.id
            
        if escola_id:
            group_name = f"school_notifications_{escola_id}"
            
        # Formata a mensagem
        user_name = instance.usuario.username if instance.usuario else "Sistema"
        action_display = instance.get_acao_display()
        obj_repr = str(instance.content_object) if instance.content_object else "Objeto desconhecido"
        
        msg_text = f"<strong>{user_name}</strong> realizou <strong>{action_display}</strong> em {obj_repr}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "message": msg_text,
                "notification_type": "info"
            }
        )
