from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from datetime import date, timedelta
from django.db import models
from core.mixins import AuditLogMixin

from escolas.models import Escola
from cursos.models import Curso, Inscricao
from alunos.models import Aluno
from core.models import Profile, AuditLog
from cursos.views import CursoListView as CursosViewBase
from alunos.views import AlunoListView as AlunosViewBase
from .forms import EscolaForm

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'escolas/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obter filtros com defaults seguros
        escola_id_filter = self.request.GET.get('escola_id')
        if not escola_id_filter or escola_id_filter == 'None':
            escola_id_filter = 'all'
        
        period_filter = self.request.GET.get('period', 'all')

        # Escopos iniciais
        aluno_scope = Aluno.objects.all()
        curso_scope = Curso.objects.all()
        inscricao_scope = Inscricao.objects.all()
        context['dashboard_title'] = "Visão Geral do Sistema"

        # Identificar escola do usuário logado
        user_escola_id = None
        if hasattr(user, 'profile') and user.profile.escola_id:
            user_escola_id = user.profile.escola_id

        # Lógica de Filtragem de Escopo
        if user.is_superuser:
            if escola_id_filter != 'all':
                try:
                    target_escola = Escola.objects.get(pk=escola_id_filter)
                    aluno_scope = aluno_scope.filter(escola=target_escola)
                    curso_scope = curso_scope.filter(escola=target_escola)
                    inscricao_scope = inscricao_scope.filter(curso__escola=target_escola)
                    context['dashboard_title'] = f"Dashboard: {target_escola.nome}"
                except (Escola.DoesNotExist, ValueError):
                    escola_id_filter = 'all'
        else:
            if user_escola_id:
                aluno_scope = aluno_scope.filter(escola_id=user_escola_id)
                curso_scope = curso_scope.filter(escola_id=user_escola_id)
                inscricao_scope = inscricao_scope.filter(curso__escola_id=user_escola_id)
                context['dashboard_title'] = user.profile.escola.nome
                escola_id_filter = str(user_escola_id)
            else:
                aluno_scope = Aluno.objects.none()
                curso_scope = Curso.objects.none()
                inscricao_scope = Inscricao.objects.none()

        # Filtro de Período
        today = date.today()
        start_date = None
        if period_filter == 'current_month':
            start_date = today.replace(day=1)
        elif period_filter == 'last_3_months':
            start_date = today - timedelta(days=90)
        elif period_filter == 'current_year':
            start_date = today.replace(month=1, day=1)

        if start_date:
            inscricao_scope = inscricao_scope.filter(data_inscricao__date__range=[start_date, today])
            curso_scope = curso_scope.filter(
                models.Q(data_inicio__range=[start_date, today]) | 
                models.Q(data_fim__range=[start_date, today])
            ).distinct()

        # Métricas (com tratamento de erro individual)
        try:
            context['total_alunos'] = aluno_scope.count()
            context['alunos_cursando'] = inscricao_scope.filter(status='cursando').count()
            context['alunos_concluintes'] = inscricao_scope.filter(status='concluido').count()
            context['alunos_desistentes'] = inscricao_scope.filter(status='desistente').count()
            context['cursos_ativos'] = curso_scope.filter(status__in=['Aberta', 'Em Andamento']).count()
            context['cursos_concluidos'] = curso_scope.filter(status='Concluído').count()
        except:
            context['total_alunos'] = 0
            context['alunos_cursando'] = 0
            context['alunos_concluintes'] = 0
            context['alunos_desistentes'] = 0
            context['cursos_ativos'] = 0
            context['cursos_concluidos'] = 0

        # Histórico Recente
        audit_scope = AuditLog.objects.select_related('usuario', 'usuario__profile', 'content_type').order_by('-data_hora')
        if not user.is_superuser:
            if user_escola_id:
                audit_scope = audit_scope.filter(usuario__profile__escola_id=user_escola_id)
            else:
                audit_scope = audit_scope.none()
        elif escola_id_filter != 'all':
            try:
                audit_scope = audit_scope.filter(usuario__profile__escola_id=int(escola_id_filter))
            except:
                pass
        
        context['historico_recente'] = audit_scope[:15]
        
        # Filtros para o Template
        context['todas_escolas'] = Escola.objects.all().order_by('nome')
        context['period_options'] = {
            'all': 'Todo o Período',
            'current_month': 'Mês Atual',
            'last_3_months': 'Últimos 3 Meses',
            'current_year': 'Ano Atual',
        }
        context['selected_escola_id'] = str(escola_id_filter)
        context['selected_period'] = period_filter
        context['is_filter_expanded'] = (escola_id_filter != 'all' or period_filter != 'all')
        context['filter_collapse_class'] = 'show' if context['is_filter_expanded'] else ''
        
        return context

class EscolaDetailView(LoginRequiredMixin, DetailView):
    model = Escola
    template_name = 'escolas/escola_detail.html'
    context_object_name = 'escola'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Escola.objects.all()
        if hasattr(user, 'profile') and user.profile.escola_id:
            return Escola.objects.filter(pk=user.profile.escola_id)
        return Escola.objects.none()

class EscolaCreateView(AuditLogMixin, SuperuserRequiredMixin, CreateView):
    model = Escola
    form_class = EscolaForm
    template_name = 'escolas/escola_form.html'
    success_url = reverse_lazy('escolas:dashboard')

class EscolaUpdateView(AuditLogMixin, SuperuserRequiredMixin, UpdateView):
    model = Escola
    form_class = EscolaForm
    template_name = 'escolas/escola_form.html'
    success_url = reverse_lazy('escolas:dashboard')

class EscolaDeleteView(AuditLogMixin, SuperuserRequiredMixin, DeleteView):
    model = Escola
    template_name = 'escolas/escola_confirm_delete.html'
    success_url = reverse_lazy('escolas:dashboard')

class CursosPorEscolaListView(CursosViewBase):
    def get_queryset(self):
        queryset = super().get_queryset()
        self.escola = get_object_or_404(Escola, pk=self.kwargs['escola_id'])
        return queryset.filter(escola=self.escola)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        return context

class AlunosPorEscolaListView(AlunosViewBase):
    def get_queryset(self):
        queryset = super().get_queryset()
        self.escola = get_object_or_404(Escola, pk=self.kwargs['escola_id'])
        return queryset.filter(escola=self.escola)
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        return context

class EscolaListView(LoginRequiredMixin, ListView):
    model = Escola
    template_name = 'escolas/escola_list.html'
    context_object_name = 'escolas'
    def get_queryset(self):
        return Escola.objects.all().order_by('nome')