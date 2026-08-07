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


class TipoCursoForm(forms.ModelForm):
    class Meta:
        model = TipoCurso
        fields = ['escola', 'nome', 'cor', 'ementa']
        widgets = {
            'escola': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'nome': forms.TextInput(attrs={'class': 'form-control form-control-premium'}),
            'cor': forms.Select(attrs={'class': 'form-select form-select-premium'}),
            'ementa': forms.Select(attrs={'class': 'form-select form-select-premium'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        active_escola = kwargs.pop('active_escola', None)
        sistema = kwargs.pop('sistema', 'CP')
        super().__init__(*args, **kwargs)
        
        if self.fields.get('escola'):
            self.fields['escola'].queryset = Escola.objects.filter(tipo=sistema).order_by('nome')
            
        if self.fields.get('cor'):
            self.fields['cor'].required = False
            self.fields['cor'].initial = 'primary'
            
        if user and not user.is_superuser:
            profile = getattr(user, 'profile', None)
            if profile and profile.escola:
                self.fields['escola'].queryset = Escola.objects.filter(pk=profile.escola.pk)
                self.fields['escola'].initial = profile.escola
                self.fields['escola'].disabled = True
            elif profile and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']:
                self.fields['escola'].queryset = Escola.objects.filter(tipo=sistema).order_by('nome')
            else:
                self.fields['escola'].queryset = self.fields['escola'].queryset.none()

    def clean_cor(self):
        cor = self.cleaned_data.get('cor')
        return cor if cor else 'primary'

class CursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'cursos/curso_list.html'
    context_object_name = 'cursos'
    def get_queryset(self):
        user = self.request.user
        sistema = self.request.session.get('sistema', 'cp').upper()
        if user.is_superuser:
            base_queryset = super().get_queryset()
        else:
            base_queryset = super().get_queryset().filter(escola__tipo=sistema)

        # Automatização de Status: Curso 'Aberta' na data de início vira 'Em Andamento'
        from datetime import date
        cursos_para_iniciar = base_queryset.filter(status='Aberta', data_inicio__lte=date.today())
        if cursos_para_iniciar.exists():
            cursos_para_iniciar.update(status='Em Andamento')
        
        active_escola = getattr(self.request, 'active_escola', None)
        active_escola_is_fallback = getattr(self.request, 'active_escola_is_fallback', False)
        profile = getattr(user, 'profile', None)

        is_global_admin = user.is_superuser or (profile and not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])

        if is_global_admin:
            qs = base_queryset
            # Filtro por Escola (Unidade) para Admin
            escola_id = self.request.GET.get('escola')
            if escola_id:
                qs = qs.filter(escola_id=escola_id)
            elif active_escola and not active_escola_is_fallback:
                qs = qs.filter(escola=active_escola)
        elif active_escola:
            qs = base_queryset.filter(escola=active_escola)
        else:
            qs = base_queryset.none()

        # Filtro de Busca (Search) para todos
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(
                Q(nome__icontains=search_query) | 
                Q(nome_professor__icontains=search_query) |
                Q(tipo_curso__nome__icontains=search_query)
            )

        # Anotações para indicadores Real-Time
        hoje = date.today()
        
        # Subquery para verificar se houve aula hoje
        sub_chamada = RegistroAula.objects.filter(
            curso=OuterRef('pk'), 
            data_aula=hoje
        )
        
        sub_qualitativo = Chamada.objects.filter(
            registro_aula__curso=OuterRef('pk'),
            registro_aula__data_aula=hoje,
            status_presenca__in=['A', 'J']
        ).filter(
            Q(motivo_falta__isnull=True) | Q(motivo_falta='')
        ).exclude(inscricao__status='desistente')

        qs = qs.annotate(
            has_chamada_hoje=Exists(sub_chamada),
            has_pendencia_qualitativa=Exists(sub_qualitativo)
        )

        return qs.order_by('-data_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pega o queryset filtrado pelo get_queryset
        all_cursos = self.get_queryset()

        # Separa os cursos em ativos e concluídos
        context['cursos_ativos'] = all_cursos.filter(status__in=['Aberta', 'Em Andamento'])
        context['cursos_concluidos'] = all_cursos.filter(status__in=['Concluído', 'Arquivado'])

        # Adiciona os tipos de curso ao contexto, como antes
        user = self.request.user
        sistema = self.request.session.get('sistema', 'cp').upper()
        if user.is_superuser:
            context['tipos_curso'] = TipoCurso.objects.all().order_by('nome')
        elif hasattr(user, 'profile') and user.profile.escola:
            context['tipos_curso'] = TipoCurso.objects.filter(escola=user.profile.escola, escola__tipo=sistema)
        else:
            context['tipos_curso'] = TipoCurso.objects.none()
        
        # Adiciona escolas para o filtro de admin
        active_escola = getattr(self.request, 'active_escola', None)
        if user.is_superuser:
            context['escolas'] = Escola.objects.all().order_by('nome')
            context['escola_selecionada'] = self.request.GET.get('escola', str(active_escola.id) if active_escola else '')
            
        return context

class CursoDetailView(LoginRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_detail.html'
    context_object_name = 'curso'

    def get_queryset(self):
        user = self.request.user
        sistema = self.request.session.get('sistema', 'cp').upper()
        active_escola = getattr(self.request, 'active_escola', None)
        is_segment_admin = hasattr(user, 'profile') and user.profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']
        qs = Curso.objects.prefetch_related('inscricao_set__aluno', 'inscricao_set__chamadas')
        if user.is_superuser:
            if active_escola:
                return qs.filter(escola=active_escola)
            return qs.all()
        if is_segment_admin:
            if active_escola:
                return qs.filter(escola=active_escola, escola__tipo=sistema)
            return qs.filter(escola__tipo=sistema)
        
        if active_escola:
            return qs.filter(escola=active_escola, escola__tipo=sistema)
            
        return Curso.objects.none()

class CursoCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'cursos/curso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.escola = self.request.user.profile.escola
        return super().form_valid(form)

class CursoUpdateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    template_name = 'cursos/curso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

class CursoDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = Curso
    template_name = 'cursos/curso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

class CursoStatusUpdateView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, View):
    model = Curso
    def post(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        novo_status = request.POST.get('status')
        
        # Bloqueia alteração se o curso estiver Concluído/Arquivado e o usuário não for superusuário ou administrador de segmento
        profile = getattr(request.user, 'profile', None)
        is_admin = request.user.is_superuser or (profile and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])
        if curso.status in ['Concluído', 'Arquivado'] and not is_admin:
            messages.error(request, "Apenas administradores podem alterar o status de um curso concluído ou arquivado.")
            return redirect('cursos:lista_cursos')

        if novo_status in [choice[0] for choice in Curso.STATUS_CHOICES]:
            # Validação: Não permitir concluir curso se houver alunos "Cursando"
            if novo_status == 'Concluído':
                # 1. Validação de Status (nenhum aluno pode estar 'cursando')
                cursando_count = curso.inscricao_set.filter(status='cursando').count()
                if cursando_count > 0:
                    messages.error(
                        request, 
                        f"Não é possível concluir o curso '{curso.nome}' porque ainda existem {cursando_count} alunos com status 'Cursando'. "
                        "Por favor, lance os concluintes e desistentes na lista de alunos antes de concluir o curso."
                    )
                    return redirect('cursos:detalhe_curso', pk=pk)

            old_status = curso.status
            curso.status = novo_status
            # Use skip to prevent duplicate signal log
            from core.utils import audit_context
            with audit_context(skip=True):
                curso.save()

            self.save_log(curso, 'UPDATE', {'status': f'"{old_status}" -> "{novo_status}"'})

        return redirect('cursos:lista_cursos')

class CursoConcluintesView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_concluintes.html'
    context_object_name = 'curso'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Curso.objects.all()
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtrar apenas as inscrições com status 'concluido'
        context['concluintes'] = self.object.inscricao_set.filter(status='concluido').select_related('aluno').order_by('aluno__nome_completo')
        return context

    def get_template_names(self):
        if self.request.GET.get('print') == '1':
            return ['cursos/curso_concluintes_print.html']
        if self.request.GET.get('popup') == '1':
            return ['cursos/curso_concluintes_modal.html']
        return [self.template_name]

class CursoConcluintesXLSXView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        if request.user.is_superuser:
            curso = get_object_or_404(Curso, pk=pk)
        else:
            curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        concluintes = curso.inscricao_set.filter(status='concluido').select_related('aluno').order_by('aluno__nome_completo')
        
        # Preparar dados para o DataFrame
        data = []
        for i, insc in enumerate(concluintes, 1):
            data.append({
                '#': i,
                'Nome do Aluno': insc.aluno.nome_completo,
                'CPF': insc.aluno.cpf,
                'Escola': curso.escola.nome,
                'Curso': curso.nome,
                'Parceiro': curso.parceiro.nome if curso.parceiro else '-',
                'Data Fim': curso.data_fim.strftime('%d/%m/%Y')
            })
            
        df = pd.DataFrame(data)
        
        # Gerar resposta Excel
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="concluintes_{curso.nome}_{curso.data_fim}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Concluintes')
            
        return response

class ExportarAlunosView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        campos_selecionados = request.POST.getlist('campos')
        
        if not campos_selecionados:
            messages.error(request, "Selecione ao menos um campo para exportar.")
            return redirect('cursos:detalhe_curso', pk=pk)

        # Filtrar alunos matriculados (cursando ou concluído)
        inscricoes = curso.inscricao_set.filter(status__in=['cursando', 'concluido']).select_related('aluno').order_by('aluno__nome_completo')
        
        data = []
        for insc in inscricoes:
            aluno = insc.aluno
            row = {}
            
            # 1. Identificação
            if 'nome' in campos_selecionados:
                row['Nome Completo'] = aluno.nome_completo
            if 'cpf' in campos_selecionados:
                row['CPF'] = aluno.cpf_formatado
            if 'rg' in campos_selecionados:
                row['RG'] = aluno.rg
            if 'orgao_exp' in campos_selecionados:
                row['Órgão Exp.'] = aluno.orgao_exp
            if 'data_emissao' in campos_selecionados:
                row['Data de Emissão'] = aluno.data_emissao.strftime('%d/%m/%Y') if aluno.data_emissao else ''
            
            # 2. Informações Pessoais
            if 'data_nascimento' in campos_selecionados:
                row['Data de Nascimento'] = aluno.data_nascimento.strftime('%d/%m/%Y') if aluno.data_nascimento else ''
            if 'idade' in campos_selecionados:
                row['Idade'] = aluno.idade
            if 'sexo' in campos_selecionados:
                row['Sexo'] = aluno.get_sexo_display()
            if 'estado_civil' in campos_selecionados:
                row['Estado Civil'] = aluno.get_estado_civil_display() if hasattr(aluno, 'get_estado_civil_display') else aluno.estado_civil
            if 'cor_raca' in campos_selecionados:
                row['Cor/Raça'] = aluno.get_cor_raca_display() if hasattr(aluno, 'get_cor_raca_display') else aluno.cor_raca
            if 'naturalidade' in campos_selecionados:
                row['Naturalidade'] = aluno.naturalidade
            if 'uf_naturalidade' in campos_selecionados:
                row['UF Naturalidade'] = aluno.uf_naturalidade
            if 'mae' in campos_selecionados:
                row['Nome da Mãe'] = aluno.nome_mae
            if 'deficiencia' in campos_selecionados:
                row['Deficiência'] = "Sim" if aluno.deficiencia else "Não"
                row['Tipo Deficiência'] = aluno.tipo_deficiencia if aluno.deficiencia else ''
            if 'escolaridade' in campos_selecionados:
                row['Escolaridade'] = aluno.get_escolaridade_display() if hasattr(aluno, 'get_escolaridade_display') else aluno.escolaridade

            # 3. Contato e Endereço
            if 'email' in campos_selecionados:
                row['Email'] = aluno.email_principal
            if 'whatsapp' in campos_selecionados:
                row['WhatsApp'] = aluno.whatsapp
            if 'telefone' in campos_selecionados:
                row['Telefone Principal'] = aluno.telefone_principal
            if 'cep' in campos_selecionados:
                row['CEP'] = aluno.endereco_cep
            if 'rua' in campos_selecionados:
                row['Rua'] = aluno.endereco_rua
            if 'numero' in campos_selecionados:
                row['Número'] = aluno.endereco_numero
            if 'bairro' in campos_selecionados:
                row['Bairro'] = aluno.endereco_bairro
            if 'cidade' in campos_selecionados:
                row['Cidade'] = aluno.endereco_cidade
            if 'estado' in campos_selecionados:
                row['Estado'] = aluno.endereco_estado
            if 'tempo_moradia' in campos_selecionados:
                row['Tempo de Moradia'] = aluno.get_tempo_moradia_display() if hasattr(aluno, 'get_tempo_moradia_display') else aluno.tempo_moradia
            if 'tipo_moradia' in campos_selecionados:
                row['Tipo de Moradia'] = aluno.get_tipo_moradia_display() if hasattr(aluno, 'get_tipo_moradia_display') else aluno.tipo_moradia
            if 'valor_moradia' in campos_selecionados:
                row['Valor da Moradia'] = f"R$ {aluno.valor_moradia}" if aluno.valor_moradia else "R$ 0,00"

            # 4. Dados Profissionais e Familiares
            if 'situacao_profissional' in campos_selecionados:
                row['Situação Profissional'] = aluno.get_situacao_profissional_display() if hasattr(aluno, 'get_situacao_profissional_display') else aluno.situacao_profissional
            if 'renda_individual' in campos_selecionados:
                row['Renda Individual'] = f"R$ {aluno.renda_individual}" if aluno.renda_individual else "R$ 0,00"
            if 'num_moradores' in campos_selecionados:
                row['Nº de Moradores'] = aluno.num_moradores
            if 'quantos_trabalham' in campos_selecionados:
                row['Quantos Trabalham'] = aluno.quantos_trabalham
            if 'renda_moradores' in campos_selecionados:
                row['Renda Outros Moradores'] = f"R$ {aluno.renda_moradores}" if aluno.renda_moradores else "R$ 0,00"
            if 'renda_familiar' in campos_selecionados:
                row['Renda Familiar'] = f"R$ {aluno.renda_familiar}"
            if 'renda_per_capita' in campos_selecionados:
                row['Renda Per Capita'] = f"R$ {aluno.renda_per_capita:.2f}"

            # 5. Outros
            if 'como_soube' in campos_selecionados:
                row['Como Soube'] = aluno.get_como_soube_display() if hasattr(aluno, 'get_como_soube_display') else aluno.como_soube
            if 'turno_interesse' in campos_selecionados:
                row['Turno de Interesse'] = aluno.turno_interesse
            if 'observacoes' in campos_selecionados:
                row['Observações'] = aluno.observacoes
            
            data.append(row)
            
        if not data:
            messages.warning(request, "Não há alunos cursando ou concluídos neste curso para exportar.")
            return redirect('cursos:detalhe_curso', pk=pk)

        df = pd.DataFrame(data)
        
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="alunos_{curso.nome}_{date.today()}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Alunos')
            
        return response

class CursoImprimirListaView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_imprimir_lista.html'
    context_object_name = 'curso'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.get_object()
        
        # Verificar permissão de escola se não for superuser
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola and user.profile.escola != curso.escola and user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
            raise PermissionDenied("Você não tem permissão para acessar esta funcionalidade.")

        context['inscricoes'] = Inscricao.objects.filter(curso=curso, status='cursando').order_by('aluno__nome_completo').select_related('aluno')
        return context

# Views para TipoCurso

class TipoCursoListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_list.html'
    context_object_name = 'tipos_curso'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        active_escola = getattr(self.request, 'active_escola', None)
        active_escola_is_fallback = getattr(self.request, 'active_escola_is_fallback', False)
        profile = getattr(self.request.user, 'profile', None)
        qs = TipoCurso.objects.filter(escola__tipo=sistema).annotate(num_interessados=Count('aluno'))
        
        is_global_admin = self.request.user.is_superuser or (profile and not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])

        if is_global_admin:
            if active_escola and not active_escola_is_fallback:
                return qs.filter(escola=active_escola)
            return qs
        
        if active_escola:
            return qs.filter(escola=active_escola)
        
        return qs.none()

class TipoCursoCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'cursos/tipocurso_form.html'
    success_url = reverse_lazy('cursos:lista_tipos_curso')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['active_escola'] = getattr(self.request, 'active_escola', None)
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.escola = self.request.user.profile.escola
        return super().form_valid(form)

class TipoCursoUpdateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, UpdateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'cursos/tipocurso_form.html'
    success_url = reverse_lazy('cursos:lista_tipos_curso')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return TipoCurso.objects.filter(escola__tipo=sistema)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['active_escola'] = getattr(self.request, 'active_escola', None)
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        return kwargs

class TipoCursoDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_tipos_curso')

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return TipoCurso.objects.filter(escola__tipo=sistema)

# Views para Inscrição
