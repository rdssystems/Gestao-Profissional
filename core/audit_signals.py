from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from core.models import AuditLog # Importar o modelo AuditLog
from django.contrib.contenttypes.models import ContentType

# Importar os modelos específicos a serem auditados
from escolas.models import Escola
from cursos.models import Curso, Inscricao
from alunos.models import Aluno
from declaracao.models import Declaracao # Import do modelo Declaracao
from controle_diario.models import ControleDiario # Import do modelo ControleDiario

# Uma função auxiliar para criar o AuditLog
def create_audit_log(sender, instance, action, user=None, **kwargs):
    from core.utils import get_current_user, get_audit_skip
    
    # Se o skip estiver ativado (pela view), não duplicamos o log do sinal
    if get_audit_skip():
        return

    if kwargs.get('raw', False): # Evita logging durante fixture loading
        return

    # Tenta obter o usuário da thread-local se não for passado e não estiver na instância
    current_user = get_current_user()
    if user is None:
        if hasattr(instance, 'usuario') and instance.usuario:
            user = instance.usuario
        elif hasattr(instance, 'emitido_por') and instance.emitido_por:
            user = instance.emitido_por
        elif hasattr(instance, 'user') and instance.user:
            user = instance.user
        elif current_user:
            user = current_user
            
    # Garantir que object_id é uma string para GenericForeignKey
    object_id_str = str(instance.pk) if instance.pk else None

    # Verificamos se já existe um log idêntico nos últimos segundos para evitar loops de sinal se houver
    AuditLog.objects.create(
        usuario=user,
        acao=action,
        content_type=ContentType.objects.get_for_model(instance),
        object_id=object_id_str,
        detalhes=f"Registro '{instance._meta.verbose_name}' ({instance}) {action.lower()}."
    )

# --- Sinais para post_save (Criação/Atualização) ---

@receiver(post_save, sender=Escola)
def log_escola_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_save, sender=Curso)
def log_curso_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_save, sender=Aluno)
def log_aluno_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_save, sender=Inscricao)
def log_inscricao_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_save, sender=Declaracao)
def log_declaracao_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)

@receiver(post_save, sender=ControleDiario)
def log_controle_diario_save(sender, instance, created, **kwargs):
    action = 'CREATE' if created else 'UPDATE'
    create_audit_log(sender, instance, action, **kwargs)


# --- Sinais para post_delete (Exclusão) ---

@receiver(post_delete, sender=Escola)
def log_escola_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_delete, sender=Curso)
def log_curso_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_delete, sender=Aluno)
def log_aluno_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_delete, sender=Inscricao)
def log_inscricao_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_delete, sender=Declaracao)
def log_declaracao_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)

@receiver(post_delete, sender=ControleDiario)
def log_controle_diario_delete(sender, instance, **kwargs):
    create_audit_log(sender, instance, 'DELETE', **kwargs)
