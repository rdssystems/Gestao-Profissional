from django.apps import AppConfig


class AlunosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alunos'

    def ready(self):
        import alunos.signals
