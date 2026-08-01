from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.contrib import messages

from .forms import UserCreationForm
from core.mixins import AuditLogMixin  # Importando o Mixin de Auditoria


def usuarios_gerenciaveis_por(request_user):
    """
    Escopo de usuarios que request_user pode listar/editar/excluir em
    usuarios/ (fora do django admin, que continua sob controle do Django).

    - Superuser: todos.
    - Administrador de segmento (perfil SEM escola vinculada e nivel_acesso
      ADMIN_CP/ADMIN_UDITECH): usuarios de escolas do seu proprio sistema.
    - Coordenador/Auxiliar (perfil COM escola vinculada): apenas usuarios da
      MESMA escola.
    Em nenhum caso um usuario nao-superuser enxerga/edita outro superuser ou
    administrador de segmento — isso fechava um caminho de escalonamento de
    privilegio (Coordenador conseguia trocar a senha de qualquer superuser).
    """
    qs = User.objects.all().select_related('profile__escola').prefetch_related('groups')

    if request_user.is_superuser:
        return qs

    profile = getattr(request_user, 'profile', None)
    if not profile:
        return qs.none()

    # Nunca expor superusers/admins de segmento a um usuario comum.
    qs = qs.filter(is_superuser=False).exclude(
        profile__nivel_acesso__in=['ADMIN_CP', 'ADMIN_UDITECH'],
        profile__escola__isnull=True,
    )

    if not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']:
        sistema = 'CP' if profile.nivel_acesso == 'ADMIN_CP' else 'UDITECH'
        return qs.filter(profile__escola__tipo=sistema)

    if profile.escola:
        return qs.filter(profile__escola=profile.escola)

    return qs.none()


class EscopoUsuarioMixin:
    """Restringe list/get_object ao escopo calculado por usuarios_gerenciaveis_por."""
    def get_queryset(self):
        return usuarios_gerenciaveis_por(self.request.user)


class UserListView(LoginRequiredMixin, PermissionRequiredMixin, EscopoUsuarioMixin, ListView):
    model = User
    template_name = 'usuarios/user_list.html'
    context_object_name = 'usuarios'
    permission_required = 'auth.view_user'


class UserCreateView(AuditLogMixin, LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    template_name = 'usuarios/user_form.html'
    success_url = reverse_lazy('usuarios:lista_usuarios')
    permission_required = 'auth.add_user'
    success_message = "Usuário '%(username)s' criado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Novo Usuário'
        return context

class UserUpdateView(AuditLogMixin, LoginRequiredMixin, PermissionRequiredMixin, EscopoUsuarioMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserCreationForm # Reusing UserCreationForm for editing
    template_name = 'usuarios/user_form.html' # Reusing the same form template
    context_object_name = 'user'
    permission_required = 'auth.change_user'
    success_url = reverse_lazy('usuarios:lista_usuarios')
    success_message = "Usuário '%(username)s' atualizado com sucesso."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Usuário: {self.object.username}'
        return context

class UserDeleteView(AuditLogMixin, LoginRequiredMixin, PermissionRequiredMixin, EscopoUsuarioMixin, DeleteView):
    model = User
    template_name = 'usuarios/user_confirm_delete.html' # Template for confirmation
    context_object_name = 'user'
    permission_required = 'auth.delete_user'
    success_url = reverse_lazy('usuarios:lista_usuarios')

    def form_valid(self, form):
        # Django >= 4.0: DeleteView.post() chama form_valid(), nao mais
        # delete() (o comentario antigo aqui estava errado desde alguma
        # atualizacao do Django — a mensagem de sucesso nunca era exibida).
        # super().form_valid() encadeia para AuditLogMixin.form_valid(),
        # que ja grava o log 'DELETE' corretamente (bug de 2026-08-01).
        obj = self.get_object()
        response = super().form_valid(form)
        messages.success(self.request, f"Usuário '{obj.username}' excluído com sucesso.")
        return response

    def dispatch(self, request, *args, **kwargs):
        # Get the object first to check if it's the current superuser
        self.object = self.get_object()
        
        # Prevent a superuser from deleting themselves if they are the logged-in superuser
        if self.object == request.user and request.user.is_superuser:
            messages.error(request, "Você não pode excluir seu próprio usuário superusuário.")
            # Redirect back to the previous page or to the list view
            return redirect(request.META.get('HTTP_REFERER', self.get_success_url()))
        
        # If not the superuser deleting themselves, proceed with the default dispatch
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Excluir Usuário: {self.object.username}'
        return context