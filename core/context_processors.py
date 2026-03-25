from .models import Aviso

def avisos_context(request):
    if request.user.is_authenticated:
        # Pega as últimas 10 atualizações
        todos_avisos = Aviso.objects.filter(ativo=True)[:10]
        # Pega o aviso ativo mais recente que o usuário ainda não visualizou (para o popup)
        proximo_aviso = Aviso.objects.filter(ativo=True).exclude(visualizado_por=request.user).first()
        # Conta quantos avisos não foram lidos
        unread_count = Aviso.objects.filter(ativo=True).exclude(visualizado_por=request.user).count()
        
        return {
            'todos_avisos': todos_avisos,
            'proximo_aviso': proximo_aviso,
            'unread_count': unread_count
        }
    return {}
