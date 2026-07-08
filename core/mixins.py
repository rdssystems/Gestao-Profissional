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
    2. Administrador de Segmento (ADMIN_CP/ADMIN_UDITECH) no portal correto.
    3. Pertence a um grupo de staff (Coordenador, Auxiliar) E está associado a uma escola.
    Para Detail/Update/Delete views, também verifica se o objeto a ser modificado
    pertence à mesma escola do usuário.
    """
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        
        profile = getattr(user, 'profile', None)
        if not profile:
            return False

        sistema = self.request.session.get('sistema', 'cp').upper()

        # Administradores de Segmento — acesso total ao seu segmento
        if profile.nivel_acesso == 'ADMIN_CP':
            return sistema == 'CP'
        if profile.nivel_acesso == 'ADMIN_UDITECH':
            return sistema == 'UDITECH'
        if profile.nivel_acesso == 'SUPERUSER':
            return True
        
        # Coordenador local / Auxiliar
        is_staff = user.groups.filter(name__in=['Coordenador', 'Auxiliar Administrativo']).exists()
        if not is_staff:
            return False

        # Se for uma view de lista ou criação, a permissão é baseada apenas no grupo do usuário.
        if isinstance(self, (CreateView, ListView)):
            return True
        
        # Para outros tipos de view, tenta verificar a permissão no nível do objeto.
        obj = None
        if hasattr(self, 'get_object'):
            try:
                obj = self.get_object()
            except Exception:
                pass
        
        if not obj:
            pk = self.kwargs.get('pk') or self.kwargs.get('id')
            if pk and hasattr(self, 'model') and self.model:
                try:
                    obj = self.model.objects.get(pk=pk)
                except Exception:
                    pass
        
        if obj:
            if hasattr(obj, 'escola') and obj.escola:
                return obj.escola == profile.escola
            elif hasattr(obj, 'curso') and hasattr(obj.curso, 'escola') and obj.curso.escola:
                return obj.curso.escola == profile.escola
            elif hasattr(obj, 'profile') and hasattr(obj.profile, 'escola') and obj.profile.escola:
                return obj.profile.escola == profile.escola
        
        return True


class CoordenadorRequiredMixin(UserPassesTestMixin):
    """
    Mixin que verifica se o usuário é:
    1. Superuser.
    2. Administrador de Segmento (ADMIN_CP/ADMIN_UDITECH) no portal correto.
    3. Pertence ao grupo 'Coordenador' E está associado a uma escola.
    """
    def test_func(self):
        user = self.request.user
        if user.is_superuser:
            return True
        
        profile = getattr(user, 'profile', None)
        if not profile:
            return False

        sistema = self.request.session.get('sistema', 'cp').upper()

        # Administradores de Segmento — acesso total ao seu segmento
        if profile.nivel_acesso == 'ADMIN_CP':
            return sistema == 'CP'
        if profile.nivel_acesso == 'ADMIN_UDITECH':
            return sistema == 'UDITECH'
        if profile.nivel_acesso == 'SUPERUSER':
            return True

        # Coordenador local
        is_coordenador = user.groups.filter(name='Coordenador').exists()
        return bool(profile.escola) and is_coordenador


class SegmentAdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin que verifica se o usuário é superusuário OU administrador de segmento (ADMIN_CP/ADMIN_UDITECH).
    """
    def test_func(self):
        user = self.request.user
        return user.is_superuser or (hasattr(user, 'profile') and user.profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])


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
        from core.utils import audit_context
        
        # O objeto já foi salvo pelo super().form_valid()
        with audit_context(skip=True):
            response = super().form_valid(form)
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
        from core.utils import audit_context
        
        # Para DeleteView, precisamos pegar o objeto ANTES de deletar
        obj = self.get_object()
        details = {'removido': str(obj)}
        
        # Ativamos o skip
        with audit_context(skip=True):
            response = super().delete(request, *args, **kwargs)
        
        # Salva o log
        self.save_log(obj, 'DELETE', details)
        
        return response
