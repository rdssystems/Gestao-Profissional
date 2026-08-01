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


class CursoAvaliacaoDashboardView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/avaliacao_dashboard.html'
    context_object_name = 'curso'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.object
        # Alunos aptos = todos que não desistiram (cursando + concluido)
        inscricoes_aptas = curso.inscricao_set.filter(status__in=['cursando', 'concluido']).select_related('aluno')
        total_aptos = inscricoes_aptas.count()
        avaliacoes_prof = AvaliacaoProfessorAluno.objects.filter(inscricao__curso=curso).count()
        avaliacoes_aluno = AvaliacaoAlunoCurso.objects.filter(inscricao__curso=curso).count()
        context['inscricoes'] = inscricoes_aptas
        context['total_concluintes'] = total_aptos
        context['avaliacoes_prof_count'] = avaliacoes_prof
        context['avaliacoes_aluno_count'] = avaliacoes_aluno
        context['perc_prof'] = int((avaliacoes_prof / total_aptos * 100)) if total_aptos > 0 else 0
        context['perc_aluno'] = int((avaliacoes_aluno / total_aptos * 100)) if total_aptos > 0 else 0
        return context

class AvaliarProfessorAcessoView(View):
    template_name = 'cursos/avaliacao_professor_acesso.html'
    def get(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        return render(request, self.template_name, {'curso': curso, 'hide_navbar': True})
    def post(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        nome_digitado = request.POST.get('professor_nome', '').strip().lower()
        nome_real = curso.nome_professor.strip().lower() if curso.nome_professor else ''
        if nome_digitado == nome_real and nome_real != '':
            request.session[f'prof_auth_{curso.pk}'] = True
            return redirect('cursos:avaliacao_professor_lista', token=token)
        else:
            from django.contrib import messages
            messages.error(request, 'Nome do professor invalido para este curso.')
            return render(request, self.template_name, {'curso': curso, 'hide_navbar': True})

class AvaliarProfessorListaView(View):
    template_name = 'cursos/avaliacao_professor_lista.html'
    def get(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        if not request.session.get(f'prof_auth_{curso.pk}'):
            return redirect('cursos:avaliacao_professor_acesso', token=token)
        # Alunos aptos = cursando + concluido (não desistentes)
        aptos = curso.inscricao_set.filter(status__in=['cursando', 'concluido']).select_related('aluno').prefetch_related('avaliacao_professor')
        return render(request, self.template_name, {'curso': curso, 'concluintes': aptos, 'hide_navbar': True})

class AvaliarEstudanteAjaxView(View):
    """
    Preenchimento da avaliacao do professor sobre um aluno especifico.
    Reaproveita a mesma sessao 'prof_auth_{curso.pk}' estabelecida em
    AvaliarProfessorAcessoView: sem ela, qualquer pessoa poderia ler/gravar
    avaliacoes de qualquer inscricao so adivinhando o pk sequencial.
    """
    def _autorizado(self, request, inscricao):
        return bool(request.session.get(f'prof_auth_{inscricao.curso_id}'))

    def get(self, request, inscricao_pk):
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
        if not self._autorizado(request, inscricao):
            raise Http404
        instance = getattr(inscricao, 'avaliacao_professor', None)
        from ..forms import AvaliacaoProfessorAlunoForm
        form = AvaliacaoProfessorAlunoForm(instance=instance)
        return render(request, 'cursos/avaliacao_professor_modal_content.html', {'form': form, 'inscricao': inscricao})
    def post(self, request, inscricao_pk):
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
        if not self._autorizado(request, inscricao):
            raise Http404
        instance = getattr(inscricao, 'avaliacao_professor', None)
        from ..forms import AvaliacaoProfessorAlunoForm
        form = AvaliacaoProfessorAlunoForm(request.POST, instance=instance)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.inscricao = inscricao
            avaliacao.professor_nome = inscricao.curso.nome_professor
            avaliacao.save()
            import json
            return HttpResponse(json.dumps({'status': 'success'}), content_type='application/json')
        import json
        return HttpResponse(json.dumps({'status': 'error', 'errors': form.errors}), content_type='application/json')

class AvaliarCursoPublicView(View):
    template_name = 'cursos/avaliacao_aluno_form.html'
    def get(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        cpf = request.GET.get('cpf')
        if not cpf:
            return render(request, 'cursos/avaliacao_aluno_identificacao.html', {'curso': curso, 'hide_navbar': True})
        
        import re
        cpf_limpo = re.sub(r'\D', '', cpf)
        from ..models import Inscricao
        
        # Busca mais robusta: 
        # 1. Permite 'concluido' OU 'cursando' (para evitar que o aluno seja bloqueado se a escola ainda não mudou o status no dia da formatura/final)
        # 2. Busca exata pelo CPF limpo
        inscricao = Inscricao.objects.filter(
            curso=curso, 
            aluno__cpf__icontains=cpf_limpo
        ).filter(status__in=['concluido', 'cursando']).first()

        if not inscricao:
            from django.contrib import messages
            messages.error(request, 'CPF não encontrado ou aluno não está apto a avaliar este curso ainda.')
            return redirect(reverse('cursos:avaliar_curso_publico', kwargs={'token': token}))
        
        # Verificar se já existe avaliação
        if hasattr(inscricao, 'avaliacao_aluno'):
            return render(request, 'cursos/avaliacao_aluno_concluida.html', {'curso': curso, 'aluno': inscricao.aluno, 'hide_navbar': True})
            
        from ..forms import AvaliacaoAlunoCursoForm
        form = AvaliacaoAlunoCursoForm()
        return render(request, self.template_name, {'curso': curso, 'aluno': inscricao.aluno, 'form': form, 'cpf': cpf, 'hide_navbar': True})

    def post(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        cpf = request.POST.get('cpf')
        import re
        cpf_limpo = re.sub(r'\D', '', cpf)
        from ..models import Inscricao, AvaliacaoAlunoCurso
        
        inscricao = get_object_or_404(Inscricao, curso=curso, aluno__cpf__icontains=cpf_limpo, status__in=['concluido', 'cursando'])
        
        from ..forms import AvaliacaoAlunoCursoForm
        form = AvaliacaoAlunoCursoForm(request.POST)
        
        if form.is_valid():
            # Usar update_or_create para evitar IntegrityError em caso de duplo clique ou resubmissão
            data = form.cleaned_data
            avaliacao, created = AvaliacaoAlunoCurso.objects.update_or_create(
                inscricao=inscricao,
                defaults=data
            )
            return render(request, 'cursos/avaliacao_aluno_concluida.html', {'curso': curso, 'aluno': inscricao.aluno, 'sucesso': True, 'hide_navbar': True})
            
        return render(request, self.template_name, {'curso': curso, 'aluno': inscricao.aluno, 'form': form, 'cpf': cpf, 'hide_navbar': True})

class ObterDadosGraficosAvaliacaoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        from ..models import AvaliacaoAlunoCurso
        from django.db.models import Count
        avaliacoes = AvaliacaoAlunoCurso.objects.filter(inscricao__curso=curso)
        stats = avaliacoes.values('c1_1').annotate(total=Count('c1_1'))
        data = {'labels': ['Otimo', 'Bom', 'Regular'], 'values': [0, 0, 0]}
        for s in stats:
            if s['c1_1'] == 'Otimo': data['values'][0] = s['total']
            elif s['c1_1'] == 'Bom': data['values'][1] = s['total']
            elif s['c1_1'] == 'Regular': data['values'][2] = s['total']
        import json
        return HttpResponse(json.dumps(data), content_type='application/json')

class AvaliacaoDetalhesView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'cursos/avaliacao_detalhes_modal.html'
    def get(self, request, inscricao_pk):
        sistema = request.session.get('sistema', 'cp').upper()
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk, curso__escola__tipo=sistema)
        return render(request, self.template_name, {
            'inscricao': inscricao,
            'av_prof': getattr(inscricao, 'avaliacao_professor', None),
            'av_aluno': getattr(inscricao, 'avaliacao_aluno', None),
        })

class CursoAvaliacaoConsolidadoView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'cursos/avaliacao_consolidado.html'

    def get_distribution(self, queryset, fields):
        from django.db.models import Count
        data = {}
        for field in fields:
            dist = queryset.values(field).annotate(total=Count(field))
            # Valor real -> Contagem
            counts = {'Otimo': 0, 'Bom': 0, 'Regular': 0}
            for d in dist:
                val = d[field]
                if val in counts:
                    counts[val] = d['total']
            data[field] = {
                'label': queryset.model._meta.get_field(field).verbose_name,
                'counts': list(counts.values()), # [Otimo, Bom, Regular]
                'labels': ['Ótimo', 'Bom', 'Regular']
            }
        return data

    def get(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        from ..models import AvaliacaoProfessorAluno, AvaliacaoAlunoCurso
        
        av_prof_qs = AvaliacaoProfessorAluno.objects.filter(inscricao__curso=curso)
        prof_fields = [
            'conceptual_pratico', 'conceptual_teorico', 'conceptual_nota',
            'behavioral_pratico', 'behavioral_teorico', 'behavioral_nota',
            'attitudinal_pratico', 'attitudinal_teorico', 'attitudinal_nota'
        ]
        prof_data = self.get_distribution(av_prof_qs, prof_fields)

        av_aluno_qs = AvaliacaoAlunoCurso.objects.filter(inscricao__curso=curso)
        aluno_fields = [
            'c1_1', 'c1_2', 'c1_3',
            'c2_1', 'c2_2', 'c2_3', 'c2_4', 'c2_5', 'c2_6', 'c2_7', 'c2_8', 'c2_9',
            'c3_1', 'c3_2', 'c3_3', 'c3_4',
            'c4_1', 'c4_2', 'c4_3', 'c4_4'
        ]
        aluno_data = self.get_distribution(av_aluno_qs, aluno_fields)

        return render(request, self.template_name, {
            'curso': curso,
            'prof_data': prof_data,
            'aluno_data': aluno_data,
            'total_prof': av_prof_qs.count(),
            'total_aluno': av_aluno_qs.count(),
        })

class CursoQualitativosView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'cursos/qualitativos_form.html'

    def get(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        data_selecionada = request.GET.get('data')
        
        chamadas = None
        if data_selecionada:
            # Encontrar registro de aula para esta data
            registro = RegistroAula.objects.filter(curso=curso, data_aula=data_selecionada).first()
            if registro:
                chamadas = Chamada.objects.filter(
                    registro_aula=registro, 
                    status_presenca__in=['A', 'J']
                ).exclude(inscricao__status='desistente')
            else:
                messages.warning(request, f"Nenhum registro de aula encontrado para a data {data_selecionada}.")

        is_modal = request.GET.get('modal') == '1'
        return render(request, self.template_name, {
            'curso': curso,
            'chamadas': chamadas,
            'data_selecionada': data_selecionada,
            'motivos': Chamada.MOTIVO_FALTA_CHOICES,
            'is_modal': is_modal,
            'hide_navbar': is_modal,
        })

    def post(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=pk, escola__tipo=sistema)
        chamadas_ids = request.POST.getlist('chamada_id')
        data_aula = request.POST.get('data_aula')
        
        from core.utils import audit_context
        with audit_context(skip=True):
            for cid in chamadas_ids:
                try:
                    chamada = Chamada.objects.get(id=cid)
                    motivo = request.POST.get(f'motivo_{cid}')
                    outro = request.POST.get(f'outro_{cid}')
                    
                    chamada.motivo_falta = motivo
                    if motivo == 'Outros':
                        chamada.motivo_falta_outro = outro
                    else:
                        chamada.motivo_falta_outro = None
                    chamada.save()
                except Chamada.DoesNotExist:
                    continue

        try:
            from core.models import AuditLog
            from django.contrib.contenttypes.models import ContentType
            AuditLog.objects.create(
                usuario=request.user,
                acao='UPDATE',
                content_type=ContentType.objects.get_for_model(curso),
                object_id=str(curso.pk),
                detalhes="Qualitativo enviado para a Turma",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception as e:
            logger.warning("Erro ao gravar log de qualitativo: %s", e)

        messages.success(request, "Motivos de falta atualizados com sucesso.")
        
        is_modal = request.POST.get('modal') == '1'
        redirect_url = reverse('cursos:curso_qualitativos', kwargs={'pk': pk}) + f"?data={data_aula}"
        if is_modal:
            redirect_url += "&modal=1"
            
        return redirect(redirect_url)
