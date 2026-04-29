import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView, TemplateView, RedirectView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from datetime import date, timedelta
from django.db import models
from django.db.models import Count, Q # Adicionados Count e Q
from core.mixins import AuditLogMixin

from django.contrib.contenttypes.models import ContentType

# Modelos importados localmente ou por classes
from escolas.models import Escola
from cursos.models import Curso, Inscricao, Chamada, AvaliacaoAlunoCurso
from alunos.models import Aluno
from core.models import Profile, AuditLog
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
        
        period_filter = self.request.GET.get('period', 'current_month')

        # Escopos iniciais
        aluno_scope = Aluno.objects.all()
        curso_scope = Curso.objects.all()

        # Automatização de Status do Curso: Aberta -> Em Andamento na data de início
        from datetime import date
        cursos_para_iniciar = curso_scope.filter(status='Aberta', data_inicio__lte=date.today())
        if cursos_para_iniciar.exists():
            cursos_para_iniciar.update(status='Em Andamento')

        inscricao_scope = Inscricao.objects.all()
        context['dashboard_title'] = "Visão Geral do Sistema"

        # Identificar escola do usuário logado
        user_escola_id = None
        if hasattr(user, 'profile') and user.profile.escola_id:
            user_escola_id = user.profile.escola_id

        # Lógica de Filtragem de Escopo Priorizando o Contexto (request.active_escola)
        target_escola = getattr(self.request, 'active_escola', None)
        
        if user.is_superuser:
            # No modo superuser, o filtro manual no dashboard sobrescreve o contexto global da sessão
            # SE o filtro for 'all', voltamos para o contexto da rede (ou da escola ativa na sessão)
            if escola_id_filter != 'all':
                try:
                    target_escola = Escola.objects.get(pk=escola_id_filter)
                except:
                    pass
        
        if target_escola:
            aluno_scope = aluno_scope.filter(escola=target_escola)
            curso_scope = curso_scope.filter(escola=target_escola)
            inscricao_scope = inscricao_scope.filter(curso__escola=target_escola)
            context['dashboard_title'] = f"Dashboard: {target_escola.nome}"
            escola_id_filter = str(target_escola.id)
        else:
            if not user.is_superuser:
                # Se não é superuser e não tem escola ativa (erro?), limpa tudo
                aluno_scope = Aluno.objects.none()
                curso_scope = Curso.objects.none()
                inscricao_scope = Inscricao.objects.none()
            else:
                context['dashboard_title'] = "Visão Geral do Sistema"
                escola_id_filter = 'all'

        # Filtro de Período Mensal
        period_filter = self.request.GET.get('mes_ano')
        today = date.today()
        if not period_filter:
            period_filter = f"{today.year}-{today.month:02d}"

        try:
            year, month = map(int, period_filter.split('-'))
        except:
            year, month = today.year, today.month
            period_filter = f"{year}-{month:02d}"

        import calendar
        _, last_day = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)

        context['mes_ano_selected'] = period_filter

        # Filtramos curso_scope para o mês (para uso nos gráficos Ocupação/Assiduidade/Demográfico que precisam dos cursos ativos no período)
        curso_scope = curso_scope.filter(
            data_inicio__lte=end_date,
            data_fim__gte=start_date
        ).distinct()

        # Métricas Globais Iniciais (com tratamento de erro individual)
        try:
            context['total_alunos'] = aluno_scope.count()
            context['alunos_cursando'] = inscricao_scope.filter(curso__in=curso_scope, status='cursando').distinct().count()
            context['alunos_concluintes'] = inscricao_scope.filter(status='concluido', data_conclusao__year=year, data_conclusao__month=month).count()
            context['alunos_concluintes_unicos'] = inscricao_scope.filter(status='concluido', data_conclusao__year=year, data_conclusao__month=month).values('aluno__cpf').distinct().count()
            context['alunos_desistentes'] = inscricao_scope.filter(status='desistente', data_desistencia__year=year, data_desistencia__month=month, chamadas__status_presenca='P').distinct().count()
            context['cursos_ativos'] = curso_scope.filter(status__in=['Aberta', 'Em Andamento']).count()
            context['cursos_concluidos'] = curso_scope.filter(status='Concluído', data_fim__year=year, data_fim__month=month).count()
            
            # Inscrições no mês (Apenas alunos criados no mês para manter retrocompatibilidade se necessário, mas o card 'Hoje' usará outra variável)
            context['inscricoes_mes'] = aluno_scope.filter(data_criacao__year=year, data_criacao__month=month).count()
        except:
            context['total_alunos'] = 0
            context['alunos_cursando'] = 0
            context['alunos_concluintes'] = 0
            context['alunos_concluintes_unicos'] = 0
            context['alunos_desistentes'] = 0
            context['cursos_ativos'] = 0
            context['cursos_concluidos'] = 0
            context['inscricoes_mes'] = 0

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
        # Preparação do Gráfico
        escolas_chart = Escola.objects.all().order_by('nome')
        if not user.is_superuser:
             if user_escola_id:
                 escolas_chart = escolas_chart.filter(id=user_escola_id)
             else:
                 escolas_chart = escolas_chart.none()
        elif escola_id_filter != 'all':
             try:
                 escolas_chart = escolas_chart.filter(id=int(escola_id_filter))
             except:
                 pass
             
        radar_fields = [
            'c3_1', 'c3_2', 'c3_3', 'c3_4'
        ]
        valor_map = {'Otimo': 3, 'Bom': 2, 'Regular': 1}
        escolas_dados = []
        
        def calcular_media_idade(query):
            idades = []
            hoje = date.today()
            for al in query:
                if al.data_nascimento:
                    idades.append(hoje.year - al.data_nascimento.year - ((hoje.month, hoje.day) < (al.data_nascimento.month, al.data_nascimento.day)))
            return int(sum(idades) / len(idades)) if idades else 0

        # ---- DADOS GLOBAIS DA REDE ----
        if user.is_superuser and (escola_id_filter == 'all' or not escola_id_filter) and escolas_chart.count() > 1:
            kpi_inscricoes_hoje_g = aluno_scope.filter(data_criacao__year=year, data_criacao__month=month).count()
            kpi_total_alunos_g = aluno_scope.count()
            kpi_alunos_cursando_g = inscricao_scope.filter(curso__in=curso_scope, status='cursando').distinct().count()
            kpi_alunos_concluintes_g = inscricao_scope.filter(status='concluido', data_conclusao__year=year, data_conclusao__month=month).count()
            kpi_alunos_concluintes_unicos_g = inscricao_scope.filter(status='concluido', data_conclusao__year=year, data_conclusao__month=month).values('aluno__cpf').distinct().count()
            kpi_alunos_desistentes_g = inscricao_scope.filter(status='desistente', data_desistencia__year=year, data_desistencia__month=month, chamadas__status_presenca='P').distinct().count()
            kpi_cursos_ativos_g = curso_scope.filter(status__in=['Aberta', 'Em Andamento']).count()
            kpi_cursos_concluidos_g = curso_scope.filter(status='Concluído', data_fim__year=year, data_fim__month=month).count()

            cursos_ativos_g = curso_scope.filter(status__in=['Aberta', 'Em Andamento'])
            vagas_g = cursos_ativos_g.aggregate(total=models.Sum('vagas'))['total'] or 0
            vagas_ociosas_g = max(0, vagas_g - kpi_alunos_cursando_g)

            # Assiduidade Geral - Agrega por Escolas em vez de curso para o Global caber
            assiduidade_labels_g = []
            assiduidade_series_g = []
            for sc in escolas_chart:
                sc_cursos = cursos_ativos_g.filter(escola=sc)
                tot_p = Chamada.objects.filter(registro_aula__curso__in=sc_cursos, status_presenca='P').count()
                tot_c = Chamada.objects.filter(registro_aula__curso__in=sc_cursos).count()
                if tot_c > 0:
                    pct = int((tot_p / tot_c) * 100)
                    assiduidade_labels_g.append(f"{sc.nome}")
                    assiduidade_series_g.append(pct)
            if assiduidade_series_g:
                a_paired_g = sorted(zip(assiduidade_labels_g, assiduidade_series_g), key=lambda x: x[1], reverse=True)[:10]
                assiduidade_labels_g, assiduidade_series_g = zip(*a_paired_g)
                assiduidade_labels_g = list(assiduidade_labels_g)
                assiduidade_series_g = list(assiduidade_series_g)

            alunos_ativos_g = aluno_scope.filter(inscricao__status='cursando', inscricao__curso__status__in=['Aberta', 'Em Andamento']).distinct()
            masc_query_g = alunos_ativos_g.filter(sexo='M')
            fem_query_g = alunos_ativos_g.filter(sexo='F')
            
            # Cálculo KPI Hoje Global
            aluno_ct = ContentType.objects.get_for_model(Aluno)
            count_novos_alunos_g = aluno_scope.filter(data_criacao__date=today).count()
            count_novas_inscricoes_g = inscricao_scope.filter(data_inscricao__date=today).count()
            
            # Interesses e Migrações via AuditLog (Global)
            audit_hoje_g = AuditLog.objects.filter(data_hora__date=today, content_type=aluno_ct, acao='UPDATE')
            count_interesses_g = 0
            count_migracoes_g = 0
            for log in audit_hoje_g:
                if log.detalhes:
                    try:
                        detalhes = json.loads(log.detalhes)
                        alteracoes = detalhes.get('alteracoes', {})
                        if 'cursos_interesse' in alteracoes: count_interesses_g += 1
                        if 'escola' in alteracoes: count_migracoes_g += 1
                    except: pass
            
            kpi_hoje_g = count_novos_alunos_g + count_novas_inscricoes_g + count_interesses_g + count_migracoes_g

            escolas_dados.append({
                'id': 'global',
                'nome': '🌐 Visão Geral da Rede',
                'kpis': {
                    'inscricoes_hoje': kpi_hoje_g,
                    'total_alunos': kpi_total_alunos_g,
                    'alunos_cursando': kpi_alunos_cursando_g,
                    'alunos_concluintes': kpi_alunos_concluintes_g,
                    'alunos_concluintes_unicos': kpi_alunos_concluintes_unicos_g,
                    'alunos_desistentes': kpi_alunos_desistentes_g,
                    'cursos_ativos': kpi_cursos_ativos_g,
                    'cursos_concluidos': kpi_cursos_concluidos_g,
                },
                'ocupacao': {
                    'vagas_total': vagas_g,
                    'labels': ['Cursando', 'Ociosas'],
                    'series': [kpi_alunos_cursando_g, vagas_ociosas_g]
                },
                'assiduidade': {
                    'labels': assiduidade_labels_g,
                    'series': assiduidade_series_g
                },
                'perfil': {
                    'series': [masc_query_g.count(), fem_query_g.count()],
                    'labels': ['Masculino', 'Feminino'],
                    'idade_media': [calcular_media_idade(masc_query_g), calcular_media_idade(fem_query_g)]
                }
            })
        
        for esc in escolas_chart:
            # 1. Dados de Ocupação (Rosca)
            esc_cursos_ativos = curso_scope.filter(escola=esc, status__in=['Aberta', 'Em Andamento'])
            vagas = esc_cursos_ativos.aggregate(total=models.Sum('vagas'))['total'] or 0
            cursando = inscricao_scope.filter(curso__escola=esc, status='cursando', curso__status__in=['Aberta', 'Em Andamento']).count()
            vagas_ociosas = max(0, vagas - cursando)
            
            # 2. Dados de Assiduidade (Barra Horizontal)
            assiduidade_labels = []
            assiduidade_series = []
            
            for curs in esc_cursos_ativos:
                tot_p = Chamada.objects.filter(registro_aula__curso=curs, status_presenca='P').count()
                tot_c = Chamada.objects.filter(registro_aula__curso=curs).count()
                if tot_c > 0:
                    pct = int((tot_p / tot_c) * 100)
                    assiduidade_labels.append(curs.nome) # limit length in JS or python?
                    assiduidade_series.append(pct)
            
            # Odenar e limitar aos 10 cursos para não explodir o card
            if assiduidade_series:
                assid_paired = list(zip(assiduidade_labels, assiduidade_series))
                assid_paired.sort(key=lambda x: x[1], reverse=True)
                assid_paired = assid_paired[:10]
                assiduidade_labels, assiduidade_series = zip(*assid_paired)
                assiduidade_labels = list(assiduidade_labels)
                assiduidade_series = list(assiduidade_series)
            
            # 3. Perfil Demográfico (Gráfico Donut - Sexo e Idade)
            alunos_ativos = aluno_scope.filter(
                inscricao__curso__escola=esc,
                inscricao__status='cursando',
                inscricao__curso__status__in=['Aberta', 'Em Andamento']
            ).distinct()
            
            masc_query = alunos_ativos.filter(sexo='M')
            fem_query = alunos_ativos.filter(sexo='F')
            
            tot_masc = masc_query.count()
            tot_fem = fem_query.count()
            
            media_idade_m = calcular_media_idade(masc_query)
            media_idade_f = calcular_media_idade(fem_query)
            
            # Cálculo KPI Hoje Individual (Escola)
            aluno_ct = ContentType.objects.get_for_model(Aluno)
            count_novos_alunos = aluno_scope.filter(escola=esc, data_criacao__date=today).count()
            count_novas_inscricoes = inscricao_scope.filter(curso__escola=esc, data_inscricao__date=today).count()
            
            # Interesses e Migrações via AuditLog (Escola)
            # Filtramos ações feitas por usuários desta escola
            audit_hoje_esc = AuditLog.objects.filter(
                data_hora__date=today, 
                content_type=aluno_ct, 
                acao='UPDATE',
                usuario__profile__escola=esc
            )
            count_interesses = 0
            count_migracoes = 0
            for log in audit_hoje_esc:
                if log.detalhes:
                    try:
                        detalhes = json.loads(log.detalhes)
                        alteracoes = detalhes.get('alteracoes', {})
                        if 'cursos_interesse' in alteracoes: count_interesses += 1
                        if 'escola' in alteracoes: count_migracoes += 1
                    except: pass
            
            kpi_hoje = count_novos_alunos + count_novas_inscricoes + count_interesses + count_migracoes

            kpi_total_alunos = aluno_scope.filter(escola=esc).count()
            kpi_alunos_cursando = inscricao_scope.filter(curso__escola=esc, curso__in=esc_cursos_ativos, status='cursando').distinct().count()
            kpi_alunos_concluintes = inscricao_scope.filter(curso__escola=esc, status='concluido', data_conclusao__year=year, data_conclusao__month=month).count()
            kpi_alunos_concluintes_unicos = inscricao_scope.filter(curso__escola=esc, status='concluido', data_conclusao__year=year, data_conclusao__month=month).values('aluno__cpf').distinct().count()
            kpi_alunos_desistentes = inscricao_scope.filter(curso__escola=esc, status='desistente', data_desistencia__year=year, data_desistencia__month=month, chamadas__status_presenca='P').distinct().count()
            kpi_cursos_ativos = esc_cursos_ativos.count()
            kpi_cursos_concluidos = curso_scope.filter(escola=esc, status='Concluído', data_fim__year=year, data_fim__month=month).count()

            # Só exibir escolas que tem ao menos um aluno ou curso rodando
            if vagas > 0 or cursando > 0 or len(assiduidade_series) > 0 or escolas_chart.count() == 1:
                escolas_dados.append({
                    'id': str(esc.id),
                    'nome': esc.nome,
                    'kpis': {
                        'inscricoes_hoje': kpi_hoje,
                        'total_alunos': kpi_total_alunos,
                        'alunos_cursando': kpi_alunos_cursando,
                        'alunos_concluintes': kpi_alunos_concluintes,
                        'alunos_concluintes_unicos': kpi_alunos_concluintes_unicos,
                        'alunos_desistentes': kpi_alunos_desistentes,
                        'cursos_ativos': kpi_cursos_ativos,
                        'cursos_concluidos': kpi_cursos_concluidos,
                    },
                    'ocupacao': {
                        'vagas_total': vagas,
                        'labels': ['Cursando', 'Ociosas'],
                        'series': [cursando, vagas_ociosas]
                    },
                    'assiduidade': {
                        'labels': assiduidade_labels,
                        'series': assiduidade_series
                    },
                    'perfil': {
                        'series': [tot_masc, tot_fem],
                        'labels': ['Masculino', 'Feminino'],
                        'idade_media': [media_idade_m, media_idade_f]
                    }
                })

        context['escolas_dados'] = escolas_dados
        context['escolas_dados_json'] = json.dumps(escolas_dados)

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

class EscolaCreateView(SuperuserRequiredMixin, CreateView):
    model = Escola
    form_class = EscolaForm
    template_name = 'escolas/escola_form.html'
    success_url = reverse_lazy('escolas:dashboard')

class EscolaUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Escola
    form_class = EscolaForm
    template_name = 'escolas/escola_form.html'
    success_url = reverse_lazy('escolas:dashboard')

class EscolaDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Escola
    template_name = 'escolas/escola_confirm_delete.html'
    success_url = reverse_lazy('escolas:dashboard')

class CursosPorEscolaListView(ListView):
    model = Curso
    template_name = 'cursos/curso_list.html'
    context_object_name = 'cursos'
    def get_queryset(self):
        self.escola = get_object_or_404(Escola, pk=self.kwargs['escola_id'])
        return Curso.objects.filter(escola=self.escola).order_by('-data_inicio')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['escola'] = self.escola
        return context

class AlunosPorEscolaListView(ListView):
    model = Aluno
    template_name = 'alunos/aluno_list.html'
    context_object_name = 'alunos'
    def get_queryset(self):
        self.escola = get_object_or_404(Escola, pk=self.kwargs['escola_id'])
        return Aluno.objects.filter(escola=self.escola).order_by('nome_completo')
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

class ConcluintesGlobalView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Curso
    template_name = 'escolas/concluintes_global.html'
    context_object_name = 'cursos_concluintes'

    def get_queryset(self):
        escola_id = self.request.GET.get('escola_id')
        # Filtra cursos que possuem pelo menos 1 aluno com status 'concluido'
        queryset = Curso.objects.annotate(
            num_concluintes=Count('inscricao', filter=Q(inscricao__status='concluido'))
        ).filter(num_concluintes__gt=0).order_by('-data_fim', 'nome')
        
        if escola_id and escola_id != 'all':
            queryset = queryset.filter(escola_id=escola_id)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['todas_escolas'] = Escola.objects.all().order_by('nome')
        context['selected_escola_id'] = self.request.GET.get('escola_id', 'all')
        return context

class AdminContextSelectView(SuperuserRequiredMixin, ListView):
    model = Escola
    template_name = 'escolas/admin_context_select.html'
    context_object_name = 'escolas'

    def get_queryset(self):
        return Escola.objects.all().order_by('nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['next_url'] = self.request.GET.get('next', reverse_lazy('escolas:dashboard'))
        return context

class AdminContextSwitchView(SuperuserRequiredMixin, View):
    def post(self, request):
        escola_id = request.POST.get('escola_id')
        if escola_id == 'all':
            if 'active_escola_id' in request.session:
                del request.session['active_escola_id']
        else:
            request.session['active_escola_id'] = escola_id
        
        next_url = request.POST.get('next', reverse_lazy('escolas:dashboard'))
        return redirect(next_url)

class AdminContextResetView(SuperuserRequiredMixin, View):
    def get(self, request):
        if 'active_escola_id' in request.session:
            del request.session['active_escola_id']
        return redirect('escolas:dashboard')

class ConcluinteUnificadoView(LoginRequiredMixin, ListView):
    model = Inscricao
    template_name = 'escolas/concluinte_unificado.html'
    context_object_name = 'concluintes'

    def get_queryset(self):
        escola_id = self.request.GET.get('escola_id')
        queryset = Inscricao.objects.filter(status='concluido').select_related(
            'aluno', 'curso', 'curso__escola', 'curso__escola__coordenador_user'
        ).order_by('curso__escola__nome', 'aluno__nome_completo')
        
        if escola_id and escola_id != 'all':
            queryset = queryset.filter(curso__escola_id=escola_id)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        concluintes = self.get_queryset()
        
        # Agrupar por escola para facilitar no template
        from itertools import groupby
        def key_func(k): return k.curso.escola
        
        grouped = []
        for escola, items in groupby(concluintes, key_func):
            grouped.append({
                'escola': escola,
                'items': list(items)
            })
            
        context['grouped_concluintes'] = grouped
        context['todas_escolas'] = Escola.objects.all().order_by('nome')
        context['selected_escola_id'] = self.request.GET.get('escola_id', 'all')
        return context