from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        import core.signals
        import core.audit_signals # Importar os novos sinais de auditoria

        # Sem 'sender=self': post_migrate dispara uma vez por app, na ordem
        # de INSTALLED_APPS. Como 'core' vem antes de 'alunos'/'cursos', se
        # o receiver so respondesse ao post_migrate do proprio 'core' as
        # Permission de Aluno/Curso/Inscricao ainda nao existiriam. Rodar em
        # TODOS os post_migrate (idempotente — so reatribui o mesmo
        # conjunto) garante que a ultima chamada da sequencia encontre tudo
        # já criado.
        from core.group_permissions import assign_default_group_permissions
        post_migrate.connect(assign_default_group_permissions)
