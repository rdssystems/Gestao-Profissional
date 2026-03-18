from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from datetime import date, timedelta # Importar date e timedelta
from django.db import models # Importar models para Q object
from core.mixins import AuditLogMixin

from escolas.models import Escola
from cursos.models import Curso, Inscricao
from alunos.models import Aluno
from cursos.views import CursoListView as CursosViewBase
from alunos.views import AlunoListView as AlunosViewBase
from .forms import EscolaForm # Adicionar este import

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class DashboardView(LoginRequiredMixin, ListView):
    model = Escola
    template_name = 'escolas/dashboard.html'
    context_object_name = 'escolas'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Escola.objects.all().order_by('nome') # Ordenar escolas para o filtro
        
        if hasattr(user, 'profile') and user.profile.escola:
            return Escola.objects.filter(pk=user.profile.escola.pk)
        
        return Escola.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obter filtros da requisição
        escola_id_filter = self.request.GET.get('escola_id')
        period_filter = self.request.GET.get('period', 'all') # Padrão 'all'

        # Definir o escopo inicial
        aluno_scope = Aluno.objects.all()
        curso_scope = Curso.objects.all()
        inscricao_scope = Inscricao.objects.all()
        context['dashboard_title'] = "Visão Geral do Sistema"

        # Aplicar filtro de escola (apenas para superusuários ou se uma escola específica for selecionada) # Correção aqui para usar str(escola.pk)
        if user.is_superuser and escola_id_filter and escola_id_filter != 'all':
            selected_escola = get_object_or_404(Escola, pk=escola_id_filter)
            aluno_scope = aluno_scope.filter(escola=selected_escola)
            curso_scope = curso_scope.filter(escola=selected_escola)
            inscricao_scope = inscricao_scope.filter(curso__escola=selected_escola)
            context['dashboard_title'] = f"Dashboard: {selected_escola.nome}"
        elif hasattr(user, 'profile') and user.profile.escola:
            # Para usuários comuns, o escopo é sempre a sua escola
            escola = user.profile.escola
            aluno_scope = aluno_scope.filter(escola=escola)
            curso_scope = curso_scope.filter(escola=escola)
            inscricao_scope = inscricao_scope.filter(curso__escola=escola)
            context['dashboard_title'] = escola.nome
            escola_id_filter = str(escola.pk) # Define o filtro da escola para o selectbox como string

        # Aplicar filtro de período
        today = date.today()
        start_date = None
        end_date = today

        if period_filter == 'current_month':
            start_date = today.replace(day=1)
        elif period_filter == 'last_3_months':
            start_date = today - timedelta(days=90)
        elif period_filter == 'current_year':
            start_date = today.replace(month=1, day=1)
        # 'all' não precisa de filtro de data

        if start_date:
            inscricao_scope = inscricao_scope.filter(data_inscricao__date__range=[start_date, end_date])
            # Para cursos, podemos filtrar por data de início ou data de fim que estejam no período
            curso_scope = curso_scope.filter(
                models.Q(data_inicio__range=[start_date, end_date]) | 
                models.Q(data_fim__range=[start_date, end_date])
            ).distinct() # Usar distinct para evitar duplicatas se um curso se encaixar em ambos os filtros Q

        # Calcula as métricas
        context['total_alunos'] = aluno_scope.count()
        context['alunos_concluintes'] = inscricao_scope.filter(status='concluido').count()
        context['alunos_desistentes'] = inscricao_scope.filter(status='desistente').count()
        context['cursos_ativos'] = curso_scope.filter(status__in=['Aberta', 'Em Andamento']).count()
        context['cursos_concluidos'] = curso_scope.filter(status='Concluído').count()
        
        # Nova métrica: Alunos Cursando
        context['alunos_cursando'] = inscricao_scope.filter(status='cursando').count()

        # Histórico recente usando AuditLog para capturar tudo (Criações, Edições, Deletados)
        from core.models import AuditLog
        
        # Filtrar logs de auditoria
        audit_scope = AuditLog.objects.select_related('usuario', 'usuario__profile', 'content_type').order_by('-data_hora')
        
        if not user.is_superuser:
            # Usuários comuns veem apenas logs de outros usuários de sua escola
            audit_scope = audit_scope.filter(usuario__profile__escola=user.profile.escola)
        elif escola_id_filter and escola_id_filter != 'all':
            # Superuser filtrando uma escola específica
            audit_scope = audit_scope.filter(usuario__profile__escola_id=escola_id_filter)
            
        context['historico_recente'] = audit_scope[:15]
        
        # Dados para o formulário de filtro no template
        context['todas_escolas'] = Escola.objects.all().order_by('nome') # Para superusers no select
        context['period_options'] = {
            'all': 'Todo o Período',
            'current_month': 'Mês Atual',
            'last_3_months': 'Últimos 3 Meses',
            'current_year': 'Ano Atual',
        }
        context['selected_escola_id'] = escola_id_filter
        context['selected_period'] = period_filter

        # Calcular is_filter_expanded (boolean) e filter_collapse_class (string) aqui na view
        is_filter_active = (escola_id_filter and escola_id_filter != 'all') or (period_filter and period_filter != 'all')
        context['is_filter_expanded'] = is_filter_active # Boolean para aria-expanded
        context['filter_collapse_class'] = 'show' if is_filter_active else '' # String para a classe do collapse
        
        return context


class EscolaDetailView(LoginRequiredMixin, DetailView):
    model = Escola
    template_name = 'escolas/escola_detail.html'
    context_object_name = 'escola'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Escola.objects.all()
        
        if hasattr(user, 'profile') and user.profile.escola:
            return Escola.objects.filter(pk=user.profile.escola.pk)
            
        return Escola.objects.none()

class EscolaCreateView(AuditLogMixin, SuperuserRequiredMixin, CreateView):
    model = Escola
    form_class = EscolaForm # Usar o formulário customizado
    template_name = 'escolas/escola_form.html'
    success_url = reverse_lazy('escolas:dashboard')

class EscolaUpdateView(AuditLogMixin, SuperuserRequiredMixin, UpdateView):
    model = Escola
    form_class = EscolaForm # Usar o formulário customizado
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

class EscolaListView(LoginRequiredMixin, ListView):
    model = Escola
    template_name = 'escolas/escola_list.html'
    context_object_name = 'escolas'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Escola.objects.all().order_by('nome')
        else:
            # Para todos os usuários autenticados que não são superusuários,
            # mostrar todas as escolas globalmente para visualização.
            return Escola.objects.all().order_by('nome')

        return context