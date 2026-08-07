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


class InscricaoCreateView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Inscricao
    form_class = InscricaoForm
    template_name = 'cursos/inscricao_form.html'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Inscricao.objects.filter(curso__escola__tipo=sistema)

    def get_success_url(self):
        return reverse_lazy('cursos:detalhe_curso', kwargs={'pk': self.object.curso.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['sistema'] = self.request.session.get('sistema', 'cp').upper()
        if 'curso_pk' in self.kwargs:
            kwargs['curso_id'] = self.kwargs['curso_pk']
        return kwargs

    def form_valid(self, form):
        aluno = form.cleaned_data['aluno']
        curso = form.cleaned_data['curso']

        if Inscricao.objects.filter(aluno=aluno, curso=curso).exists():
            messages.error(self.request, f'O aluno {aluno.nome_completo} já está inscrito no curso {curso.nome}.')
            return self.form_invalid(form)
        
        if curso.status not in ['Aberta', 'Em Andamento']:
            messages.error(self.request, f'Não é possível inscrever alunos no curso {curso.nome} pois o status é "{curso.status}".')
            return self.form_invalid(form)

        # --- Lógica de validação de conflitos de matrícula usando a função auxiliar ---
        try:
            validar_conflito_matricula(aluno, curso)
        except ValidationError as e:
            messages.error(self.request, e.message)
            return self.form_invalid(form)
        # --- Fim da lógica de validação ---

        messages.success(self.request, f'Aluno {aluno.nome_completo} inscrito com sucesso no curso {curso.nome}.')
        return super().form_valid(form)

class UpdateInscricaoStatusView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, SingleObjectMixin, View):
    model = Inscricao

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Inscricao.objects.filter(curso__escola__tipo=sistema)

    def post(self, request, pk):
        inscricao = self.get_object()
        
        novo_status = request.POST.get('status')
        if novo_status in ['concluido', 'desistente', 'cursando']:
            if novo_status == 'desistente':
                tem_presenca = inscricao.chamadas.filter(status_presenca='P').exists()
                if not tem_presenca:
                    messages.error(
                        request,
                        f"Não é possível marcar '{inscricao.aluno.nome_completo}' como desistente pois o aluno não possui nenhuma presença registrada nas listas de frequência. Só pode ser marcado como desistente quem já participou ao menos uma vez das aulas. Quem nunca participou deve ser excluído do curso se não for continuar."
                    )
                    return redirect('cursos:detalhe_curso', pk=inscricao.curso.pk)

            inscricao.status = novo_status
            from core.utils import audit_context
            with audit_context(skip=True):
                inscricao.save()

            self.save_log(inscricao, 'UPDATE', {'status': novo_status})

            # Se o aluno concluiu o curso, removemos este tipo de curso dos interesses dele
            if novo_status == 'concluido':
                tipo_curso = inscricao.curso.tipo_curso
                if tipo_curso in inscricao.aluno.cursos_interesse.all():
                    inscricao.aluno.cursos_interesse.remove(tipo_curso)

            messages.success(request, f"Status do aluno '{inscricao.aluno.nome_completo}' atualizado para '{inscricao.get_status_display()}'.")
        else:
            messages.error(request, "Status inválido.")
            
        return redirect('cursos:detalhe_curso', pk=inscricao.curso.pk)

class MatriculaView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Aluno
    template_name = 'cursos/matricula_page.html'
    context_object_name = 'alunos_sugeridos'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        curso_id = self.request.GET.get('curso_id')
        if not curso_id:
            return Aluno.objects.none()

        curso = get_object_or_404(Curso, pk=curso_id, status__in=['Aberta', 'Em Andamento'], escola__tipo=sistema)
        
        # Filtrar alunos que têm o tipo de curso do curso selecionado em seus interesses
        # e que ainda não estão inscritos neste curso.
        alunos_interessados = Aluno.objects.filter(
            cursos_interesse=curso.tipo_curso,
            escola__tipo=sistema
        )
        
        ids_alunos_ja_inscritos = Inscricao.objects.filter(curso=curso).values_list('aluno_id', flat=True)
        
        # Priorizar alunos cujo turno_interesse corresponde ao turno do curso (usando icontains pois agora pode ter vários)
        qs = alunos_interessados.exclude(id__in=ids_alunos_ja_inscritos).annotate(
            turno_match=Case(
                When(turno_interesse__icontains=curso.turno, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
        
        # Anotar o status do contato de matrícula para o curso selecionado
        status_subquery = ContatoMatricula.objects.filter(
            aluno=OuterRef('pk'),
            curso=curso
        ).values('status')[:1]
        
        qs = qs.annotate(contato_status=Subquery(status_subquery))
        
        qs = qs.order_by('-turno_match', '-score_total')
        
        # Filtra por escola ativa (Contexto Admin ou Perfil Staff)
        active_escola = getattr(self.request, 'active_escola', None)
        if active_escola:
            qs = qs.filter(escola=active_escola)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        sistema = self.request.session.get('sistema', 'cp').upper()
        
        # Queryset de cursos abertos ou em andamento para o seletor
        cursos_abertos_qs = Curso.objects.filter(status__in=['Aberta', 'Em Andamento'], escola__tipo=sistema)
        active_escola = getattr(self.request, 'active_escola', None)
        if active_escola:
            cursos_abertos_qs = cursos_abertos_qs.filter(escola=active_escola)
        
        context['cursos_abertos'] = cursos_abertos_qs
        
        curso_id = self.request.GET.get('curso_id')
        if curso_id:
            context['selected_curso'] = get_object_or_404(Curso, pk=curso_id, escola__tipo=sistema)
            context['alunos_matriculados'] = Inscricao.objects.filter(curso=context['selected_curso'], status='cursando').order_by('aluno__nome_completo')
            
            # Adicionar as escolhas de status ao contexto
            context['contato_status_choices'] = ContatoMatricula.STATUS_CHOICES
            
        return context

class AtualizarContatoMatriculaAjaxView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            aluno_id = data.get('aluno_id')
            curso_id = data.get('curso_id')
            status = data.get('status')
            
            if not aluno_id or not curso_id or not status:
                return JsonResponse({'success': False, 'error': 'Parâmetros incompletos.'}, status=400)
                
            sistema = request.session.get('sistema', 'cp').upper()
            aluno = get_object_or_404(Aluno, pk=aluno_id, escola__tipo=sistema)
            curso = get_object_or_404(Curso, pk=curso_id, escola__tipo=sistema)
            
            # Validar se o status é uma opção válida
            valid_statuses = [choice[0] for choice in ContatoMatricula.STATUS_CHOICES]
            if status not in valid_statuses:
                return JsonResponse({'success': False, 'error': 'Status inválido.'}, status=400)
                
            contato, created = ContatoMatricula.objects.update_or_create(
                aluno=aluno,
                curso=curso,
                defaults={'status': status}
            )
            
            return JsonResponse({
                'success': True, 
                'status': contato.status, 
                'status_display': contato.get_status_display()
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

class MatricularAlunoDiretoView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        aluno_id = request.POST.get('aluno_id')
        curso_id = request.POST.get('curso_id')
        
        sistema = request.session.get('sistema', 'cp').upper()
        aluno = get_object_or_404(Aluno, pk=aluno_id, escola__tipo=sistema)
        curso = get_object_or_404(Curso, pk=curso_id, escola__tipo=sistema)

        # URL de redirecionamento em caso de sucesso ou erro
        redirect_url = reverse('cursos:matricula') + f'?curso_id={curso_id}'

        # Verifica se o aluno já está inscrito
        if Inscricao.objects.filter(aluno=aluno, curso=curso).exists():
            messages.warning(request, f'O aluno {aluno.nome_completo} já está matriculado neste curso.')
            return redirect(redirect_url)

        # --- Lógica de validação de conflitos de matrícula usando a função auxiliar ---
        try:
            validar_conflito_matricula(aluno, curso)
        except ValidationError as e:
            messages.error(request, e.message)
            return redirect(redirect_url)
        # --- Fim da lógica de validação ---

        from core.utils import audit_context
        with audit_context(skip=True):
            # Cria a inscrição
            inscricao = Inscricao.objects.create(aluno=aluno, curso=curso)

        self.save_log(inscricao, 'CREATE', {'matricula_direta': f"{aluno.nome_completo} em {curso.nome}"})

        messages.success(request, f'Aluno {aluno.nome_completo} matriculado com sucesso no curso {curso.nome}.')
        return redirect(redirect_url)

class CancelarMatriculaDiretoView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        inscricao_id = request.POST.get('inscricao_id')
        sistema = request.session.get('sistema', 'cp').upper()
        inscricao = get_object_or_404(Inscricao, pk=inscricao_id, curso__escola__tipo=sistema)
        curso_id = inscricao.curso.pk
        
        # Confirmação adicional de permissão (escola) se necessário, mas CoordenadorRequiredMixin + filtro inicial já ajuda
        # Vamos garantir que o coordenador é da mesma escola se não for superuser
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.escola != inscricao.curso.escola:
                messages.error(request, "Você não tem permissão para cancelar matrículas desta escola.")
                return redirect(reverse('cursos:matricula') + f'?curso_id={curso_id}')

        aluno_nome = inscricao.aluno.nome_completo
        curso_nome = inscricao.curso.nome

        # Loga ANTES de deletar: inscricao.delete() zera o pk da instância,
        # e self.save_log() precisa de obj.pk para montar o object_id.
        self.save_log(inscricao, 'DELETE', {'cancelamento_direto': f"{aluno_nome} do curso {curso_nome}"})

        from core.utils import audit_context
        with audit_context(skip=True):
            inscricao.delete()
        
        messages.success(request, f"Matrícula de {aluno_nome} cancelada com sucesso.")
        return redirect(reverse('cursos:matricula') + f'?curso_id={curso_id}')

class InscricaoDeleteView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Inscricao
    template_name = 'cursos/inscricao_confirm_delete.html' # Pode ser um template genérico ou um específico
    context_object_name = 'inscricao'

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Inscricao.objects.filter(curso__escola__tipo=sistema)

    def get_success_url(self):
        # Redireciona de volta para a página de detalhes do curso
        messages.success(self.request, f"Matrícula de '{self.object.aluno.nome_completo}' no curso '{self.object.curso.nome}' removida com sucesso.")
        return reverse_lazy('cursos:detalhe_curso', kwargs={'pk': self.object.curso.pk})
