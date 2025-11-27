from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

class StaffRequiredMixin(UserPassesTestMixin):
    """
    Mixin que verifica se o usuário é:
    1. Superuser.
    2. Pertence a um grupo de staff (Coordenador, Auxiliar) E está associado a uma escola.
    Para Detail/Update/Delete views, também verifica se o objeto a ser modificado
    pertence à mesma escola do usuário.
    """
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        
        if hasattr(user, 'profile') and user.profile.escola:
            is_staff = user.groups.filter(name__in=['Coordenador', 'Auxiliar Administrativo']).exists()
            if not is_staff:
                return False

            # Se for uma view de lista ou criação, a permissão é baseada apenas no grupo do usuário.
            if isinstance(self, (CreateView, ListView)):
                return True
            
            # Para outros tipos de view, tenta verificar a permissão no nível do objeto.
            if hasattr(self, 'get_object'):
                obj = self.get_object()
                if hasattr(obj, 'escola'):
                    return obj.escola == user.profile.escola
                elif hasattr(obj, 'curso') and hasattr(obj.curso, 'escola'):
                    return obj.curso.escola == user.profile.escola
                elif hasattr(obj, 'profile') and hasattr(obj.profile, 'escola'):
                    return obj.profile.escola == user.profile.escola
            
            # Se a view não tem get_object (ex: uma View de ação), a verificação de grupo é suficiente.
            # A view é responsável por sua própria lógica de permissão interna.
            return True


        return False
