from .utils import set_current_user

class ThreadLocalUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user)
        try:
            response = self.get_response(request)
        finally:
            set_current_user(None)
        return response

class AdminContextMiddleware:
    """
    Middleware que define request.active_escola baseado na sessão (superuser/segment admins)
    ou no perfil do usuário (coord/auxiliar).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_escola = None
        request.active_escola_is_fallback = False
        if request.user.is_authenticated:
            # 1. Se vier o parâmetro "sistema" na URL (GET ou POST), atualiza a sessão
            sistema_param = request.GET.get('sistema') or request.POST.get('sistema')
            if sistema_param:
                sistema_param = sistema_param.lower()
                if sistema_param in ['cp', 'uditech']:
                    request.session['sistema'] = sistema_param
            
            profile = getattr(request.user, 'profile', None)
            
            # 2. Fallback de segurança para garantir que o "sistema" na sessão esteja correto
            if 'sistema' not in request.session:
                if profile:
                    if profile.escola:
                        request.session['sistema'] = profile.escola.tipo.lower()
                    elif profile.nivel_acesso == 'ADMIN_UDITECH':
                        request.session['sistema'] = 'uditech'
                    elif profile.nivel_acesso == 'ADMIN_CP':
                        request.session['sistema'] = 'cp'
                    else:
                        request.session['sistema'] = 'cp'
                else:
                    request.session['sistema'] = 'cp'
            
            # 3. Forçar o portal correto baseado no perfil se o usuário não for superuser
            if profile and not request.user.is_superuser:
                if profile.nivel_acesso == 'ADMIN_UDITECH' and request.session.get('sistema') != 'uditech':
                    request.session['sistema'] = 'uditech'
                elif profile.nivel_acesso == 'ADMIN_CP' and request.session.get('sistema') != 'cp':
                    request.session['sistema'] = 'cp'
                elif profile.escola and request.session.get('sistema') != profile.escola.tipo.lower():
                    request.session['sistema'] = profile.escola.tipo.lower()

            sistema = request.session.get('sistema', 'cp').upper()
            request.sistema = sistema

            # Se for superuser ou administrador de segmento (nao estando nos grupos de escola)
            is_segment_admin = (profile and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']
                                and not request.user.groups.filter(name__in=['Coordenador', 'Auxiliar Administrativo']).exists())
            if request.user.is_superuser or is_segment_admin:
                escola_id = request.session.get('active_escola_id')
                if escola_id and str(escola_id).isdigit():
                    from django.apps import apps
                    Escola = apps.get_model('escolas', 'Escola')
                    try:
                        if request.user.is_superuser:
                            escola = Escola.objects.filter(id=escola_id).first()
                        else:
                            escola = Escola.objects.filter(id=escola_id, tipo=sistema).first()

                        if escola:
                            if request.user.is_superuser:
                                request.active_escola = escola
                                request.session['sistema'] = escola.tipo.lower()
                            elif profile.nivel_acesso == 'ADMIN_UDITECH' and sistema == 'UDITECH':
                                request.active_escola = escola
                            elif profile.nivel_acesso == 'ADMIN_CP' and sistema == 'CP':
                                request.active_escola = escola
                    except:
                        request.active_escola = None
                # Nenhum fallback automático — sem escola selecionada, active_escola fica None
                # e a navbar exibirá "Visão Global"
            elif profile and profile.escola:
                # Coordenador local / Auxiliar: fixado na escola do perfil
                if profile.escola.tipo == sistema:
                    request.active_escola = profile.escola

        return self.get_response(request)
