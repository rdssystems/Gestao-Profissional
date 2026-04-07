from .utils import set_current_user

class ThreadLocalUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user)
        response = self.get_response(request)
        # Opcional: set_current_user(None) no final para limpar
        return response
