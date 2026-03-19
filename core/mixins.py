from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.contenttypes.models import ContentType
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict

# Import local para evitar erro de importação circular se colocar no topo
# (mas idealmente models devem ser importados no topo se não houver ciclo)

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
class CoordenadorRequiredMixin(UserPassesTestMixin):
    """
    Mixin que verifica se o usuário é:
    1. Superuser.
    2. Pertence ao grupo 'Coordenador' E está associado a uma escola.
    """
    def test_func(self):
        user = self.request.user
        import sys
        
        if user.is_superuser:
            # sys.stderr.write(f"DEBUG: Superuser {user.username} access granted.\n")
            return True
        
        has_profile = hasattr(user, 'profile')
        has_escola = bool(user.profile.escola) if has_profile else False
        is_coordenador = user.groups.filter(name='Coordenador').exists()
        
        res = has_profile and has_escola and is_coordenador
        
        if not res:
            sys.stderr.write(f"DEBUG 403: User={user.username}, Profile={has_profile}, Escola={has_escola}, Coord={is_coordenador}\n")
            
        return res


class AuditLogMixin:
    """
    Mixin para registrar logs de auditoria automaticamente em CreateView, UpdateView e DeleteView.
    """

    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def save_log(self, obj, action, details=None):
        from core.models import AuditLog  # Importação tardia para evitar ciclo

        user = self.request.user if self.request.user.is_authenticated else None
        
        try:
            AuditLog.objects.create(
                usuario=user,
                acao=action,
                content_type=ContentType.objects.get_for_model(obj),
                object_id=str(obj.pk) if obj.pk else None,
                detalhes=json.dumps(details, cls=DjangoJSONEncoder, ensure_ascii=False) if details else None,
                ip_address=self.get_client_ip()
            )
        except Exception as e:
            print(f"Erro ao salvar log de auditoria: {e}")

    def form_valid(self, form):
        # Capturar ação baseada na View
        response = super().form_valid(form)
        
        # O objeto já foi salvo pelo super().form_valid()
        obj = self.object
        
        action = 'UPDATE'
        details = {}

        # Se for CreateView, o objeto acabou de ser criado
        if isinstance(self, CreateView):
            action = 'CREATE'
            # Para create, salvamos uma representação simples
            details = {'novo': str(obj)}
        elif isinstance(self, UpdateView):
            action = 'UPDATE'
            if form.changed_data:
                changes = {}
                for field in form.changed_data:
                    # Tenta pegar o valor limpo
                    value = form.cleaned_data.get(field)
                    # Se for um objeto (ForeignKey), converte pra string
                    changes[field] = str(value)
                details = {'alteracoes': changes}
            else:
                details = {'info': 'Nenhum campo alterado.'}

        self.save_log(obj, action, details)
        return response

    def delete(self, request, *args, **kwargs):
        # Para DeleteView, precisamos pegar o objeto ANTES de deletar
        obj = self.get_object()
        details = {'removido': str(obj)}
        
        # Chama o delete original (que deleta o objeto)
        response = super().delete(request, *args, **kwargs)
        
        # Salva o log
        self.save_log(obj, 'DELETE', details)
        
        return response
