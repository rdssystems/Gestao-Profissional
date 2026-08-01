import csv
import io
import json
import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import pandas as pd
from django.db.models import Count, Prefetch, Exists, OuterRef, Q, Case, When, Value, IntegerField, Sum, Subquery # Import Count
from datetime import date, time, datetime # Import datetime and time
from django.http import HttpResponse, Http404, JsonResponse

from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin # Import UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render # Adicionar render aqui
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError 
from django import forms
from django.forms import inlineformset_factory # Adicionar import

# Importar modelos e formulários
from ..models import Curso, TipoCurso, Inscricao, RegistroAula, Chamada, Parceiro, EmentaPadrao, AvaliacaoProfessorAluno, AvaliacaoAlunoCurso, ContatoMatricula # Adicionar RegistroAula, Chamada, Parceiro, EmentaPadrao, AvaliacaoProfessorAluno, AvaliacaoAlunoCurso
from ..forms import CursoForm, InscricaoForm, RegistroAulaForm, ChamadaFormSet, CursoCSVUploadForm, ChamadaForm, ParceiroForm, EmentaPadraoForm # Adicionar ParceiroForm, EmentaPadraoForm
from core.mixins import StaffRequiredMixin, AuditLogMixin, CoordenadorRequiredMixin

logger = logging.getLogger(__name__)
from alunos.models import Aluno
from ..validators import validar_conflito_matricula 

from escolas.models import Escola
# from datetime import date # Para usar date.today()


# Formulário para TipoCurso


class ParceiroListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Parceiro
    template_name = 'cursos/parceiro_list.html'
    context_object_name = 'parceiros'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        active_escola = getattr(self.request, 'active_escola', None)
        active_escola_is_fallback = getattr(self.request, 'active_escola_is_fallback', False)
        profile = getattr(self.request.user, 'profile', None)

        is_global_admin = self.request.user.is_superuser or (profile and not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])

        if is_global_admin:
            if active_escola and not active_escola_is_fallback:
                return Parceiro.objects.filter(escola=active_escola, escola__tipo=sistema).order_by('nome')
            return Parceiro.objects.filter(escola__tipo=sistema).order_by('escola__nome', 'nome')
        
        if active_escola:
            return Parceiro.objects.filter(escola=active_escola, escola__tipo=sistema).order_by('nome')
            
        return Parceiro.objects.none()

class ParceiroCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'cursos/parceiro_form.html'
    success_url = reverse_lazy('cursos:lista_parceiros')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.escola = self.request.user.profile.escola
        return super().form_valid(form)

class ParceiroUpdateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, UpdateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'cursos/parceiro_form.html'
    success_url = reverse_lazy('cursos:lista_parceiros')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Parceiro.objects.filter(escola__tipo=sistema)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

class ParceiroDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = Parceiro
    template_name = 'cursos/curso_confirm_delete.html' 
    success_url = reverse_lazy('cursos:lista_parceiros')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Parceiro.objects.filter(escola__tipo=sistema)

# --- CRUD para Ementa Padrão (Global - Admin) ---

class EmentaPadraoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = EmentaPadrao
    template_name = 'cursos/ementapadrao_list.html'
    context_object_name = 'ementas'

    def test_func(self):
        return self.request.user.is_superuser

class EmentaPadraoCreateView(LoginRequiredMixin, UserPassesTestMixin, AuditLogMixin, CreateView):
    model = EmentaPadrao
    form_class = EmentaPadraoForm
    template_name = 'cursos/ementapadrao_form.html'
    success_url = reverse_lazy('cursos:lista_ementas')

    def test_func(self):
        return self.request.user.is_superuser

class EmentaPadraoUpdateView(LoginRequiredMixin, UserPassesTestMixin, AuditLogMixin, UpdateView):
    model = EmentaPadrao
    form_class = EmentaPadraoForm
    template_name = 'cursos/ementapadrao_form.html'
    success_url = reverse_lazy('cursos:lista_ementas')

    def test_func(self):
        return self.request.user.is_superuser

class EmentaPadraoDeleteView(LoginRequiredMixin, UserPassesTestMixin, AuditLogMixin, DeleteView):
    model = EmentaPadrao
    template_name = 'cursos/curso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_ementas')

    def test_func(self):
        return self.request.user.is_superuser

class ObterEmentaView(LoginRequiredMixin, View):
    """View para retornar o conteúdo da ementa via requisição (pode ser usada em modal)"""
    def get(self, request, pk):
        ementa = get_object_or_404(EmentaPadrao, pk=pk)
        return render(request, 'cursos/ementa_modal_content.html', {'ementa': ementa})
# --- Novas Views para Sistema de Avaliacoes ---
