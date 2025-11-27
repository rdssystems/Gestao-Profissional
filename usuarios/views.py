from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.contrib import messages

from .forms import UserCreationForm

class UserListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = 'usuarios/user_list.html'
    context_object_name = 'usuarios'
    permission_required = 'auth.view_user'

    def get_queryset(self):
        # Prefetch related objects to avoid N+1 queries in the template
        return User.objects.all().select_related('profile__escola').prefetch_related('groups')


class UserCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    template_name = 'usuarios/user_form.html'
    success_url = reverse_lazy('usuarios:lista_usuarios')
    permission_required = 'auth.add_user'
    success_message = "Usuário '%(username)s' criado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Criar Novo Usuário'
        return context

class UserUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserCreationForm # Reusing UserCreationForm for editing
    template_name = 'usuarios/user_form.html' # Reusing the same form template
    context_object_name = 'user'
    permission_required = 'auth.change_user'
    success_url = reverse_lazy('usuarios:lista_usuarios')
    success_message = "Usuário '%(username)s' atualizado com sucesso."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Editar Usuário: {self.object.username}'
        return context

class UserDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = 'usuarios/user_confirm_delete.html' # Template for confirmation
    context_object_name = 'user'
    permission_required = 'auth.delete_user'
    success_url = reverse_lazy('usuarios:lista_usuarios')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Usuário '{obj.username}' excluído com sucesso.")
        return super(UserDeleteView, self).delete(request, *args, **kwargs)

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

    # Removed the custom delete method override, relying on SuccessMessageMixin
    # def delete(self, request, *args, **kwargs):
    #     ...

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Excluir Usuário: {self.object.username}'
        return context