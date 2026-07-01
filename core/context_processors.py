from .models import Aviso, AgendamentoEmail

def avisos_context(request):
    if request.user.is_authenticated:
        todos_avisos = Aviso.objects.filter(ativo=True)[:10]
        proximo_aviso = Aviso.objects.filter(ativo=True).exclude(visualizado_por=request.user).first()
        unread_count = Aviso.objects.filter(ativo=True).exclude(visualizado_por=request.user).count()
        active_escola = getattr(request, 'active_escola', None)
        sistema = getattr(request, 'sistema', 'CP')

        alerta = AgendamentoEmail.get_alert_context()

        return {
            'todos_avisos': todos_avisos,
            'proximo_aviso': proximo_aviso,
            'unread_count': unread_count,
            'active_escola': active_escola,
            **alerta,
        }
    return {}
