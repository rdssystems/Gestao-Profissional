from .utils import set_current_user

class ThreadLocalUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user)
        response = self.get_response(request)
        return response

class AdminContextMiddleware:
    """
    Middleware que define request.active_escola baseado na sessão (superuser)
    ou no perfil do usuário (coord/auxiliar).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.active_escola = None
        if request.user.is_authenticated:
            if request.user.is_superuser:
                escola_id = request.session.get('active_escola_id')
                if escola_id and str(escola_id).isdigit():
                    from django.apps import apps
                    Escola = apps.get_model('escolas', 'Escola')
                    try:
                        request.active_escola = Escola.objects.filter(id=escola_id).first()
                    except:
                        request.active_escola = None
            elif hasattr(request.user, 'profile') and request.user.profile.escola:
                request.active_escola = request.user.profile.escola
            
        return self.get_response(request)
