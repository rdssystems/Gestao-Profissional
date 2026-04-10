import csv
import io
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import pandas as pd
from django.db.models import Count, Prefetch, Exists, OuterRef, Q, Case, When, Value, IntegerField, Sum # Import Count
from datetime import date, time, datetime # Import datetime and time
from django.http import HttpResponse, Http404

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
from .models import Curso, TipoCurso, Inscricao, RegistroAula, Chamada, Parceiro, EmentaPadrao, AvaliacaoProfessorAluno, AvaliacaoAlunoCurso # Adicionar RegistroAula, Chamada, Parceiro, EmentaPadrao, AvaliacaoProfessorAluno, AvaliacaoAlunoCurso
from .forms import CursoForm, InscricaoForm, RegistroAulaForm, ChamadaFormSet, CursoCSVUploadForm, ChamadaForm, ParceiroForm, EmentaPadraoForm # Adicionar ParceiroForm, EmentaPadraoForm
from core.mixins import StaffRequiredMixin, AuditLogMixin, CoordenadorRequiredMixin
from alunos.models import Aluno
from .validators import validar_conflito_matricula 

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
        super().__init__(*args, **kwargs)
        
        if user and not user.is_superuser and hasattr(user, 'profile') and user.profile.escola:
            self.fields['escola'].queryset = Escola.objects.filter(pk=user.profile.escola.pk)
            self.fields['escola'].initial = user.profile.escola
            self.fields['escola'].disabled = True
        elif not user.is_superuser:
            self.fields['escola'].queryset = self.fields['escola'].queryset.none()


class CursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'cursos/curso_list.html'

    def get_queryset(self):
        user = self.request.user
        base_queryset = super().get_queryset()
        
        if user.is_superuser:
            qs = base_queryset
            # Filtro por Escola (Unidade) para Admin
            escola_id = self.request.GET.get('escola')
            if escola_id:
                qs = qs.filter(escola_id=escola_id)
        elif hasattr(user, 'profile') and user.profile.escola:
            qs = base_queryset.filter(escola=user.profile.escola)
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
        if user.is_superuser:
            context['tipos_curso'] = TipoCurso.objects.all()
        elif hasattr(user, 'profile') and user.profile.escola:
            context['tipos_curso'] = TipoCurso.objects.filter(escola=user.profile.escola)
        else:
            context['tipos_curso'] = TipoCurso.objects.none()
        
        # Adiciona escolas para o filtro de admin
        if user.is_superuser:
            context['escolas'] = Escola.objects.all().order_by('nome')
            
        return context

class CursoDetailView(LoginRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_detail.html'
    context_object_name = 'curso'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Curso.objects.all()
        
        if hasattr(user, 'profile') and user.profile.escola:
            return Curso.objects.filter(escola=user.profile.escola)
            
        return Curso.objects.none()

class CursoCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'cursos/curso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class CursoDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = Curso
    template_name = 'cursos/curso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_cursos')

from django.contrib.contenttypes.models import ContentType # Import ContentType
from core.models import AuditLog # Import AuditLog

class CursoStatusUpdateView(LoginRequiredMixin, StaffRequiredMixin, View):
    model = Curso
    def post(self, request, pk):
        curso = get_object_or_404(Curso, pk=pk)
        novo_status = request.POST.get('status')
        
        # Bloqueia alteração se o curso estiver Concluído/Arquivado e o usuário não for superusuário
        if curso.status in ['Concluído', 'Arquivado'] and not request.user.is_superuser:
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

                # 2. Validação de Avaliações (Professor e Aluno) - COMENTADO PARA FUTURA HABILITAÇÃO
                """
                inscricoes_concluidas = curso.inscricao_set.filter(status='concluido')
                total_concluintes = inscricoes_concluidas.count()
                
                # Se houver concluintes, validar avaliações
                if total_concluintes > 0:
                    # Avaliações do Professor (100% dos concluintes)
                    # Usamos Count com o related_name 'avaliacao_professor'
                    prof_eval_count = AvaliacaoProfessorAluno.objects.filter(inscricao__curso=curso, inscricao__status='concluido').count()
                    
                    # Avaliações dos Alunos (50% dos concluintes)
                    # Usamos Count com o related_name 'avaliacao_aluno'
                    student_eval_count = AvaliacaoAlunoCurso.objects.filter(inscricao__curso=curso, inscricao__status='concluido').count()
                    
                    min_student_eval = (total_concluintes + 1) // 2  # Metade arredondada para cima
                    
                    erros_avaliacao = []
                    
                    if prof_eval_count < total_concluintes:
                        erros_avaliacao.append(f"Faltam {total_concluintes - prof_eval_count} avaliações de desempenho do professor.")
                    
                    if student_eval_count < min_student_eval:
                        erros_avaliacao.append(f"Faltam {min_student_eval - student_eval_count} avaliações de feedback dos alunos (necessário pelo menos 50%).")
                    
                    if erros_avaliacao:
                        msg = f"Não é possível concluir o curso '{curso.nome}' devido a pendências: " + " ".join(erros_avaliacao)
                        messages.warning(request, msg)
                        return redirect('cursos:detalhe_curso', pk=pk)
                elif total_concluintes == 0:
                    # Se não houver concluintes (apenas desistentes), permite concluir mas avisa
                    messages.info(request, "O curso está sendo concluído sem nenhum aluno aprovado (apenas desistentes).")
                """

            old_status = curso.status
            curso.status = novo_status
            # Use skip to prevent duplicate signal log
            from core.utils import audit_context
            with audit_context(skip=True):
                curso.save()
            
            try:
                AuditLog.objects.create(
                    usuario=request.user,
                    acao='UPDATE',
                    content_type=ContentType.objects.get_for_model(curso),
                    object_id=str(curso.pk),
                    detalhes=f'Status alterado de "{old_status}" para "{novo_status}"',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception as e:
                print(f"Erro ao gerar log de auditoria manual: {e}")

        return redirect('cursos:lista_cursos')

class CursoConcluintesView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_concluintes.html'
    context_object_name = 'curso'

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
        curso = get_object_or_404(Curso, pk=pk)
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

class CursoImprimirListaView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/curso_imprimir_lista.html'
    context_object_name = 'curso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.get_object()
        
        # Verificar permissão de escola se não for superuser
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola != curso.escola:
            raise PermissionDenied("Você não tem permissão para acessar esta funcionalidade.")

        context['inscricoes'] = Inscricao.objects.filter(curso=curso, status='cursando').order_by('aluno__nome_completo').select_related('aluno')
        return context

# Views para TipoCurso
class TipoCursoListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_list.html'
    context_object_name = 'tipos_curso'

    def get_queryset(self):
        user = self.request.user
        qs = TipoCurso.objects.all().annotate(num_interessados=Count('aluno'))
        
        if user.is_superuser:
            return qs
        
        if hasattr(user, 'profile') and user.profile.escola:
            return qs.filter(escola=user.profile.escola)
        
        return qs.none()

class TipoCursoCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'cursos/tipocurso_form.html'
    success_url = reverse_lazy('cursos:lista_tipos_curso')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class TipoCursoDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_tipos_curso')

# Views para Inscrição
class InscricaoCreateView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = Inscricao
    form_class = InscricaoForm
    template_name = 'cursos/inscricao_form.html'

    def get_success_url(self):
        return reverse_lazy('cursos:detalhe_curso', kwargs={'pk': self.object.curso.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
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

class UpdateInscricaoStatusView(LoginRequiredMixin, StaffRequiredMixin, SingleObjectMixin, View):
    model = Inscricao

    def post(self, request, pk):
        inscricao = self.get_object()
        
        novo_status = request.POST.get('status')
        if novo_status in ['concluido', 'desistente', 'cursando']:
            inscricao.status = novo_status
            from core.utils import audit_context
            with audit_context(skip=True):
                inscricao.save()

            # Log manual para WS
            try:
                AuditLog.objects.create(
                    usuario=request.user,
                    acao='UPDATE',
                    content_type=ContentType.objects.get_for_model(inscricao),
                    object_id=str(inscricao.pk),
                    detalhes=f"Status inscrição alterado para {novo_status}",
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            except Exception as e:
                print(f"Erro log status inscricao: {e}")

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
        curso_id = self.request.GET.get('curso_id')
        if not curso_id:
            return Aluno.objects.none()

        curso = get_object_or_404(Curso, pk=curso_id, status__in=['Aberta', 'Em Andamento'])
        
        # Filtrar alunos que têm o tipo de curso do curso selecionado em seus interesses
        # e que ainda não estão inscritos neste curso.
        alunos_interessados = Aluno.objects.filter(
            cursos_interesse=curso.tipo_curso
        )
        
        ids_alunos_ja_inscritos = Inscricao.objects.filter(curso=curso).values_list('aluno_id', flat=True)
        
        qs = alunos_interessados.exclude(id__in=ids_alunos_ja_inscritos).order_by('-score_total')
        
        # Filtra por escola, se o usuário não for superuser
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola:
            return qs.filter(escola=user.profile.escola)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Queryset de cursos abertos ou em andamento para o seletor
        cursos_abertos_qs = Curso.objects.filter(status__in=['Aberta', 'Em Andamento'])
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola:
            cursos_abertos_qs = cursos_abertos_qs.filter(escola=user.profile.escola)
        
        context['cursos_abertos'] = cursos_abertos_qs
        
        curso_id = self.request.GET.get('curso_id')
        if curso_id:
            context['selected_curso'] = get_object_or_404(Curso, pk=curso_id)
            context['alunos_matriculados'] = Inscricao.objects.filter(curso=context['selected_curso'], status='cursando').order_by('aluno__nome_completo')
            
        return context

class MatricularAlunoDiretoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        aluno_id = request.POST.get('aluno_id')
        curso_id = request.POST.get('curso_id')
        
        aluno = get_object_or_404(Aluno, pk=aluno_id)
        curso = get_object_or_404(Curso, pk=curso_id)

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
            
        # Log manual
        try:
            AuditLog.objects.create(
                usuario=request.user,
                acao='CREATE',
                content_type=ContentType.objects.get_for_model(inscricao),
                object_id=str(inscricao.pk),
                detalhes=f"Matrícula direta de {aluno.nome_completo} em {curso.nome}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception as e:
            print(f"Erro log matricula direta: {e}")

        messages.success(request, f'Aluno {aluno.nome_completo} matriculado com sucesso no curso {curso.nome}.')

        return redirect(redirect_url)

class CancelarMatriculaDiretoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        inscricao_id = request.POST.get('inscricao_id')
        inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
        curso_id = inscricao.curso.pk
        
        # Confirmação adicional de permissão (escola) se necessário, mas CoordenadorRequiredMixin + filtro inicial já ajuda
        # Vamos garantir que o coordenador é da mesma escola se não for superuser
        if not request.user.is_superuser:
            if hasattr(request.user, 'profile') and request.user.profile.escola != inscricao.curso.escola:
                messages.error(request, "Você não tem permissão para cancelar matrículas desta escola.")
                return redirect(reverse('cursos:matricula') + f'?curso_id={curso_id}')

        aluno_nome = inscricao.aluno.nome_completo
        curso_nome = inscricao.curso.nome
        inscricao_id = inscricao.pk
        # Salva o content type antes de deletar
        inscricao_content_type = ContentType.objects.get_for_model(inscricao)
        
        from core.utils import audit_context
        with audit_context(skip=True):
            inscricao.delete()
            
        # Log manual para WS
        try:
            AuditLog.objects.create(
                usuario=request.user,
                acao='DELETE',
                content_type=inscricao_content_type,
                object_id=str(inscricao_id),
                detalhes=f"Cancelamento direto: {aluno_nome} do curso {curso_nome}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception as e:
            print(f"Erro log cancelamento: {e}")
        
        messages.success(request, f"Matrícula de {aluno_nome} cancelada com sucesso.")
        return redirect(reverse('cursos:matricula') + f'?curso_id={curso_id}')

class InscricaoDeleteView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, DeleteView):
    model = Inscricao
    template_name = 'cursos/inscricao_confirm_delete.html' # Pode ser um template genérico ou um específico
    context_object_name = 'inscricao'

    def get_success_url(self):
        # Redireciona de volta para a página de detalhes do curso
        messages.success(self.request, f"Matrícula de '{self.object.aluno.nome_completo}' no curso '{self.object.curso.nome}' removida com sucesso.")
        return reverse_lazy('cursos:detalhe_curso', kwargs={'pk': self.object.curso.pk})

class ChamadaCursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'cursos/lista_chamadas_cursos.html'
    context_object_name = 'cursos_para_chamada'
    
    def get_queryset(self):
        user = self.request.user
        queryset = Curso.objects.filter(status__in=['Aberta', 'Em Andamento']) # Filtrar por status ativo

        if user.is_superuser:
            return queryset
        
        if hasattr(user, 'profile') and user.profile.escola:
            return queryset.filter(escola=user.profile.escola)
        
        return Curso.objects.none()

# Nova View para Fazer/Editar Chamada
class FazerChamadaView(LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'cursos/fazer_chamada.html'

    def get(self, request, curso_pk, registro_aula_pk=None):
        curso = get_object_or_404(Curso, pk=curso_pk)
        
        # Verificar permissão de escola se não for superuser
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola != curso.escola:
            raise PermissionDenied("Você não tem permissão para acessar chamadas deste curso.")

        registro_aula = None
        if registro_aula_pk:
            registro_aula = get_object_or_404(RegistroAula, pk=registro_aula_pk, curso=curso)
            form = RegistroAulaForm(instance=registro_aula, curso=curso)
        else:
            # Tentar encontrar um registro de aula para hoje para este curso
            registro_aula = RegistroAula.objects.filter(curso=curso, data_aula=date.today()).first()
            if registro_aula:
                form = RegistroAulaForm(instance=registro_aula, curso=curso)
                messages.info(request, f"Já existe um registro de aula para {curso.nome} em {date.today().strftime('%d/%m/%Y')}. Editando o registro existente.")
            else:
                form = RegistroAulaForm(initial={'curso': curso, 'data_aula': date.today()}, curso=curso)

        # Definir as inscrições que PODEM estar na chamada (ativos e desistentes)
        inscricoes_elegiveis = Inscricao.objects.filter(curso=curso, status__in=['cursando', 'desistente']).order_by('aluno__nome_completo')
        
        # 1. Obter inscrições que JÁ têm registro nesta aula
        inscricoes_com_registro = []
        if registro_aula:
            inscricoes_com_registro = Chamada.objects.filter(registro_aula=registro_aula).values_list('inscricao_id', flat=True)
        
        # 2. Identificar inscrições faltantes (estão no curso mas não no registro desta aula)
        inscricoes_faltantes = inscricoes_elegiveis.exclude(id__in=inscricoes_com_registro)
        
        initial_faltantes = []
        for insc in inscricoes_faltantes:
            initial_faltantes.append({'inscricao': insc, 'status_presenca': 'A'})
            
        # 3. Criar FormSet dinâmico
        # Se existem faltantes, precisamos de 'extra' forms para eles
        num_faltantes = len(initial_faltantes)
        
        ChamadaDynamicFormSet = inlineformset_factory(
            RegistroAula, 
            Chamada, 
            form=ChamadaForm, 
            extra=num_faltantes, 
            can_delete=False, 
            fields=['inscricao', 'status_presenca']
        )
        
        if registro_aula:
            formset = ChamadaDynamicFormSet(instance=registro_aula, initial=initial_faltantes, prefix='chamada')
        else:
            formset = ChamadaDynamicFormSet(instance=None, initial=initial_faltantes, prefix='chamada')

        # 4. Garantir que aluno_nome é exibido para todos os forms (existentes e extras)
        for f in formset:
            insc_obj = None
            if f.instance and f.instance.pk and hasattr(f.instance, 'inscricao'):
                insc_obj = f.instance.inscricao
            elif f.initial and f.initial.get('inscricao'):
                insc_obj = f.initial.get('inscricao')
            
            if insc_obj:
                # Verificamos se f.fields['aluno_nome'] existe (pode ser None no management form do inline?)
                if 'aluno_nome' in f.fields:
                    f.fields['aluno_nome'].initial = insc_obj.aluno.nome_completo


        context = {
            'curso': curso,
            'form': form,
            'formset': formset,
            'registro_aula': registro_aula,
        }
        return render(request, self.template_name, context)

    def post(self, request, curso_pk, registro_aula_pk=None):
        curso = get_object_or_404(Curso, pk=curso_pk)

        # Verificar permissão de escola se não for superuser
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola != curso.escola:
            raise PermissionDenied("Você não tem permissão para acessar chamadas deste curso.")

        # 1. Tentar encontrar ou definir o RegistroAula com base na data do POST
        registro_aula = None
        data_str = request.POST.get('data_aula')
        data_obj = None
        
        if data_str:
            try:
                data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if registro_aula_pk:
            registro_aula = get_object_or_404(RegistroAula, pk=registro_aula_pk, curso=curso)
            # Se a data no POST for diferente da data original do registro_aula_pk,
            # verifica se já existe outro registro para essa nova data
            if data_obj and registro_aula.data_aula != data_obj:
                novo_registro = RegistroAula.objects.filter(curso=curso, data_aula=data_obj).first()
                if novo_registro:
                    messages.info(request, f"A data foi alterada para {data_obj.strftime('%d/%m/%Y')}, que já possui uma chamada registrada. Redirecionando para a edição desta data.")
                    return redirect('cursos:fazer_chamada_editar', curso_pk=curso.pk, registro_aula_pk=novo_registro.pk)
        elif data_obj:
            registro_aula = RegistroAula.objects.filter(curso=curso, data_aula=data_obj).first()
            if registro_aula:
                messages.info(request, f"Já existe uma chamada registrada em {data_obj.strftime('%d/%m/%Y')}. Redirecionando para a edição.")
                return redirect('cursos:fazer_chamada_editar', curso_pk=curso.pk, registro_aula_pk=registro_aula.pk)

        # 2. TRATAMENTO CRITICAL: Se o usuário mudou a data, os IDs e Vínculos no formset estão obsoletos
        # Precisamos limpá-los para evitar "Parent Mismatch" (O valor na linha não correspondeu com a instância pai).
        post_data = request.POST.copy()
        management_total = int(post_data.get('chamada-TOTAL_FORMS', 0))
        
        mudou_para_novo = False
        for i in range(management_total):
            id_key = f'chamada-{i}-id'
            parent_key = f'chamada-{i}-registro_aula' # O campo que causa o erro do usuário
            form_cid = post_data.get(id_key)
            
            # Se a data mudou (registro_aula novo ou diferente), limpamos ID e o vínculo com o Pai antigo
            if not registro_aula or (form_cid and not Chamada.objects.filter(pk=form_cid, registro_aula=registro_aula).exists()):
                if id_key in post_data: post_data[id_key] = ''
                if parent_key in post_data: post_data[parent_key] = '' # Limpa o vínculo do aluno com o dia anterior
                mudou_para_novo = True
        
        if mudou_para_novo and not registro_aula:
            if 'chamada-INITIAL_FORMS' in post_data:
                post_data['chamada-INITIAL_FORMS'] = 0

        form = RegistroAulaForm(request.POST, instance=registro_aula, curso=curso)
        formset = ChamadaFormSet(post_data, instance=registro_aula, prefix='chamada') 

        if form.is_valid() and formset.is_valid():
            registro_aula_instance = form.save(commit=False)
            registro_aula_instance.curso = curso 
            registro_aula_instance.save() 

            formset.instance = registro_aula_instance
            
            # Salvar chamadas
            for form_chamada in formset:
                if form_chamada.instance.pk:
                    form_chamada.save()
                else:
                    if any(form_chamada.cleaned_data.values()):
                        chamada = form_chamada.save(commit=False)
                        chamada.registro_aula = registro_aula_instance
                        
                        # Recuperar inscrição se não houver
                        if not chamada.inscricao_id:
                             inscricao = form_chamada.cleaned_data.get('inscricao')
                             if inscricao:
                                 chamada.inscricao = inscricao
                        
                        if chamada.inscricao:
                             # Evitar duplicados para a mesma aula
                             if not Chamada.objects.filter(registro_aula=registro_aula_instance, inscricao=chamada.inscricao).exists():
                                 chamada.save()

            messages.success(request, f"Chamada para o dia {registro_aula_instance.data_aula.strftime('%d/%m/%Y')} salva com sucesso.")
            return redirect('cursos:lista_cursos')
        else:
            # Capturar erros específicos
            error_list = []
            if form.errors:
                for field, errors in form.errors.items():
                    error_list.append(f"{field}: {', '.join(errors)}")
            
            if formset.errors:
                for i, f_errors in enumerate(formset.errors):
                    if f_errors:
                        aluno_n = f"Aluno #{i+1}"
                        try:
                             insc_id = request.POST.get(f'chamada-{i}-inscricao')
                             if insc_id:
                                 insc = Inscricao.objects.select_related('aluno').get(pk=insc_id)
                                 aluno_n = insc.aluno.nome_completo
                        except: pass
                        
                        for field, errors in f_errors.items():
                            error_list.append(f"{aluno_n} ({field}): {', '.join(errors)}")
            
            if formset.non_form_errors():
                error_list.extend(formset.non_form_errors())

            messages.error(request, "Erro na submissão: " + " | ".join(error_list))
            
            # Repopular nomes e inscrições para evitar VariableDoesNotExist no template
            for i, f in enumerate(formset):
                try:
                    # Tenta obter o ID da inscrição do POST ou do initial
                    insc_id = request.POST.get(f'chamada-{i}-inscricao')
                    if not insc_id and f.initial:
                        insc_id = f.initial.get('inscricao')
                    
                    if insc_id:
                        insc_obj = Inscricao.objects.select_related('aluno').filter(pk=insc_id).first()
                        if insc_obj:
                            # Adiciona ao initial para que o template {% with inscricao=... %} funcione
                            if f.initial is None: f.initial = {}
                            f.initial['inscricao'] = insc_obj
                            # Garante que o campo de nome também esteja preenchido
                            f.fields['aluno_nome'].initial = insc_obj.aluno.nome_completo
                except Exception as e:
                    print(f"Erro ao repopular form #{i}: {e}")

            context = {
                'curso': curso,
                'form': form,
                'formset': formset,
                'registro_aula': registro_aula,
            }
            return render(request, self.template_name, context)

class HistoricoChamadasCursoView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = RegistroAula
    template_name = 'cursos/historico_chamadas_curso.html'
    context_object_name = 'registros_aula'
    paginate_by = 30 # Aumentado para ver mais dias

    def get_queryset(self):
        self.curso = get_object_or_404(Curso, pk=self.kwargs['curso_pk'])
        
        # Verificar permissão de escola se não for superuser
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola != self.curso.escola:
            raise PermissionDenied("Você não tem permissão para acessar o histórico de chamadas deste curso.")
            
        return RegistroAula.objects.filter(curso=self.curso).order_by('-data_aula')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['curso'] = self.curso
        return context

class RelatorioFrequenciaView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/relatorio_frequencia.html'
    context_object_name = 'curso'
    pk_url_kwarg = 'curso_pk'

    def get_object(self, queryset=None):
        return get_object_or_404(Curso, pk=self.kwargs['curso_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.get_object()
        
        # Verificar permissão de escola
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola != curso.escola:
            raise PermissionDenied("Você não tem permissão para acessar o relatório deste curso.")

        # Buscar todos os registros de aula do curso ordendos por data (antigas para novas)
        registros = RegistroAula.objects.filter(curso=curso).order_by('data_aula')
        
        # Buscar alunos (cursando e desistentes)
        # Ordenação: Cursando primeiro (ordem alfabética), depois Desistentes (ordem alfabética)
        inscricoes = Inscricao.objects.filter(curso=curso).annotate(
            is_desistente=Case(
                When(status='desistente', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('is_desistente', 'aluno__nome_completo').select_related('aluno')

        # Criar matriz de frequência
        matriz_frequencia = []
        
        # Cache das chamadas num dicionário de busca rápida
        resumo_chamadas = {
            (c.inscricao_id, c.registro_aula_id): c.status_presenca 
            for c in Chamada.objects.filter(registro_aula__curso=curso)
        }

        total_presentes = 0
        total_ausentes = 0

        for inscricao in inscricoes:
            linha_aluno = {
                'aluno': inscricao.aluno.nome_completo,
                'inscricao_id': inscricao.id,
                'status': inscricao.status,
                'presencas': [],
                'total_presencas': 0,
                'total_aulas_registradas': 0
            }
            for reg in registros:
                status = resumo_chamadas.get((inscricao.id, reg.id), '—')
                linha_aluno['presencas'].append({
                    'status': status,
                    'data': reg.data_aula
                })
                
                # Contabilizar para o aluno individualmente (apenas se houver P, A ou J)
                if status in ['P', 'A', 'J']:
                    linha_aluno['total_aulas_registradas'] += 1
                
                # Contabilizar totais globais e individuais
                if status == 'P':
                    total_presentes += 1
                    linha_aluno['total_presencas'] += 1
                elif status == 'A':
                    total_ausentes += 1
                elif status == 'J':
                    # Opcional: Você pode querer contabilizar justificativa como presença ou neutro
                    # Por enquanto, J conta como aula registrada mas não como presença.
                    pass
            
            # Calcular porcentagem de frequência individual
            if linha_aluno['total_aulas_registradas'] > 0:
                linha_aluno['porcentagem_freq'] = int((linha_aluno['total_presencas'] / linha_aluno['total_aulas_registradas']) * 100)
            else:
                linha_aluno['porcentagem_freq'] = 0

            matriz_frequencia.append(linha_aluno)

        # Calculando totais por registro (coluna) para exibir no final da tabela
        totais_colunas = []
        for reg in registros:
            # Contar status 'P' e 'A' para este registro específico
            p_count = Chamada.objects.filter(registro_aula=reg, status_presenca='P').count()
            a_count = Chamada.objects.filter(registro_aula=reg, status_presenca='A').count()
            totais_colunas.append({
                'registro_id': reg.id,
                'presencas': p_count,
                'ausencias': a_count
            })

        context['registros'] = registros
        context['matriz'] = matriz_frequencia
        context['totais_colunas'] = totais_colunas
        context['total_presentes'] = total_presentes
        context['total_ausentes'] = total_ausentes
        return context

class ExcluirRegistroAulaView(LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        registro = get_object_or_404(RegistroAula, pk=pk)
        curso = registro.curso
        
        # Verificar permissão de escola se não for superuser
        user = request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola != curso.escola:
            raise PermissionDenied("Você não tem permissão para excluir registros desta escola.")
            
        data_formatada = registro.data_aula.strftime('%d/%m/%Y')
        registro.delete()
        
        # Log manual para auditoria
        try:
            from core.models import AuditLog
            from django.contrib.contenttypes.models import ContentType
            AuditLog.objects.create(
                usuario=request.user,
                acao='DELETE',
                content_type=ContentType.objects.get_for_model(RegistroAula),
                object_id=str(pk),
                detalhes=f"Registro de aula ({data_formatada}) excluído para o curso {curso.nome}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
        except Exception as e:
            print(f"Erro ao gerar log de exclusão de chamada: {e}")

        messages.success(request, f"O registro de presença do dia {data_formatada} para o curso '{curso.nome}' foi removido com sucesso!")
        return redirect('cursos:relatorio_frequencia', curso_pk=curso.pk)

class CursoCSVUploadView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'cursos/upload_cursos_csv.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_uploaded_file(self, file):
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        # Lista para armazenar cursos criados/atualizados e erros
        created_count = 0
        updated_count = 0
        errors = []

        for i, row in enumerate(reader):
            line_num = i + 2 # +1 for 0-indexed, +1 for header
            try:
                # 1. Get Escola by name (do not create if not found)
                escola_nome = row.get('escola_nome')
                if not escola_nome: # Validar campo obrigatório
                    raise ValueError("Coluna 'escola_nome' é obrigatória.")
                
                try:
                    escola = Escola.objects.get(nome=escola_nome)
                except Escola.DoesNotExist:
                    raise ValueError(f"Escola '{escola_nome}' não encontrada. As escolas devem ser criadas antes do upload do CSV.")

                # 2. Get or create TipoCurso (using nome_curso as type name)
                nome_curso = row.get('nome_curso') # Need nome_curso first for TipoCurso
                if not nome_curso: 
                    raise ValueError("Coluna 'nome_curso' é obrigatória.")

                tipo_curso_nome_for_tag = nome_curso # TipoCurso will have the same name as the course
                tipo_curso_cor = row.get('tipo_curso_cor', 'primary')
                # Ensure cor is one of the valid choices
                if tipo_curso_cor not in [choice[0] for choice in TipoCurso.COR_CHOICES]:
                    tipo_curso_cor = 'primary' # Fallback to default if invalid
                tipo_curso, _ = TipoCurso.objects.get_or_create(escola=escola, nome=tipo_curso_nome_for_tag, defaults={'cor': tipo_curso_cor})
                # If existing TipoCurso has different color, update it
                if tipo_curso.cor != tipo_curso_cor:
                    tipo_curso.cor = tipo_curso_cor
                    tipo_curso.save()

                # 3. Create or update Curso
                carga_horaria = int(row.get('carga_horaria')) if row.get('carga_horaria') else None
                if carga_horaria is None or carga_horaria <= 0: # Validar carga_horaria
                    raise ValueError("Coluna 'carga_horaria' é obrigatória e deve ser um número positivo.")

                data_inicio_str = row.get('data_inicio')
                data_fim_str = row.get('data_fim')

                if not data_inicio_str or not data_fim_str:
                     raise ValueError("Colunas 'data_inicio' e 'data_fim' são obrigatórias.")

                data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
                data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

                if data_inicio > data_fim:
                    raise ValueError("'data_inicio' não pode ser posterior a 'data_fim'.")

                status_curso = 'Aberta' # Always default to 'Aberta' as per requirement
                
                turno = row.get('turno', None)
                if turno and turno not in [choice[0] for choice in Curso.TURNOS_CHOICES]:
                    turno = None # Fallback if invalid

                horario_str = row.get('horario', None)
                horario = datetime.strptime(horario_str, '%H:%M').time() if horario_str else None

                curso_defaults = {
                    'carga_horaria': carga_horaria,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim,
                    'status': status_curso,
                    'turno': turno,
                    'horario': horario,
                    'tipo_curso': tipo_curso,
                    'escola': escola,
                }
                curso, created = Curso.objects.update_or_create(
                    escola=escola, 
                    nome=nome_curso,
                    defaults=curso_defaults
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except (ValueError, KeyError, ValidationError, Escola.DoesNotExist) as e:
                errors.append(f"Linha {line_num}: {e}")
            except Exception as e:
                errors.append(f"Linha {line_num}: Erro inesperado - {e}")
        
        return created_count, updated_count, errors

    def get(self, request, *args, **kwargs):
        form = CursoCSVUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = CursoCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            # Validate file type
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Por favor, envie um arquivo CSV válido.")
                return render(request, self.template_name, {'form': form})

            created_count, updated_count, errors = self.handle_uploaded_file(csv_file)

            if errors:
                for error in errors:
                    messages.error(request, error)
                messages.warning(request, f"Processamento concluído com {created_count} cursos criados, {updated_count} cursos atualizados e erros em algumas linhas.")
            else:
                messages.success(request, f"Upload de CSV concluído com sucesso: {created_count} cursos criados, {updated_count} cursos atualizados.")
            
            return redirect('cursos:lista_cursos') # Redirect to course list or calendar after upload
        else:
            return render(request, self.template_name, {'form': form})

class DownloadCursoTemplateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        cols = [
            'escola_nome', 'nome_curso', 'carga_horaria', 'data_inicio', 
            'data_fim', 'turno', 'horario', 'tipo_curso_cor'
        ]
        df = pd.DataFrame(columns=cols)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="template_importacao_cursos.xlsx"'
class ChamadaPublicaView(View):
    template_name = 'cursos/chamada_publica.html'

    def get(self, request, token):
        curso = Curso.objects.filter(token_acesso=token).first()
        if not curso:
            raise Http404("Curso não encontrado.")
            
        # Verificar se o professor está autenticado na sessão para este token específico
        auth_key = f'auth_chamada_{token}'
        is_authenticated = request.session.get(auth_key, False)
        
        if not is_authenticated:
            return render(request, self.template_name, {
                'curso': curso,
                'precisa_auth': True
            })

        if curso.status in ['Concluído', 'Arquivado']:
            return render(request, self.template_name, {
                'curso': curso,
                'erro_status': f"Este curso já está {curso.status.lower()} e não aceita mais chamadas via link público."
            })
            
        hoje = date.today()
        
        # --- DADOS PARA ABA: REGISTRAR CHAMADA ---
        registro_hoje, _ = RegistroAula.objects.get_or_create(
            curso=curso, 
            data_aula=hoje,
            defaults={'observacoes': 'Chamada realizada via link público.'}
        )
        presencas_hoje = Chamada.objects.filter(registro_aula=registro_hoje, status_presenca='P').values_list('inscricao__aluno_id', flat=True)
        inscricoes = Inscricao.objects.filter(curso=curso, status='cursando').select_related('aluno')
        
        alunos_lista = []
        for insc in inscricoes:
            alunos_lista.append({
                'id': insc.id,
                'nome': insc.aluno.nome_completo,
                'presente': insc.aluno.id in presencas_hoje
            })
        alunos_lista = sorted(alunos_lista, key=lambda x: x['nome'])

        # --- DADOS PARA ABA: HISTÓRICO ---
        historico_registros = RegistroAula.objects.filter(curso=curso).order_by('-data_aula')
        historico_lista = []
        
        # Buscamos todas as chamadas do curso de uma vez para otimizar
        todas_chamadas = Chamada.objects.filter(registro_aula__curso=curso).select_related('inscricao__aluno')
        
        for reg in historico_registros:
            chamadas_reg = [c for c in todas_chamadas if c.registro_aula_id == reg.id]
            total_alunos = len(chamadas_reg)
            presentes = len([c for c in chamadas_reg if c.status_presenca == 'P'])
            ausentes = len([c for c in chamadas_reg if c.status_presenca == 'A'])
            
            detalhes_alunos = []
            for c in chamadas_reg:
                detalhes_alunos.append({
                    'nome': c.inscricao.aluno.nome_completo,
                    'status': 'Presente' if c.status_presenca == 'P' else 'Ausente'
                })
            detalhes_alunos = sorted(detalhes_alunos, key=lambda x: x['nome'])

            historico_lista.append({
                'data': reg.data_aula,
                'presentes': presentes,
                'ausentes': ausentes,
                'total': total_alunos,
                'detalhes': detalhes_alunos
            })
        
        context = {
            'curso': curso,
            'hoje': hoje,
            'alunos_lista': alunos_lista,
            'historico_lista': historico_lista,
            'is_authenticated': True
        }
        return render(request, self.template_name, context)

    def post(self, request, token):
        curso = Curso.objects.filter(token_acesso=token).first()
        if not curso:
            raise Http404("Curso não encontrado.")
            
        action = request.POST.get('action')
        auth_key = f'auth_chamada_{token}'

        # LÓGICA DE LOGIN
        if action == 'login':
            nome_input = request.POST.get('nome_professor', '').strip().lower()
            nome_cadastrado = (curso.nome_professor or "").strip().lower()
            
            if nome_input == nome_cadastrado and nome_cadastrado != "":
                request.session[auth_key] = True
                messages.success(request, f"Bem-vindo(a), Professor(a) {curso.nome_professor}!")
            else:
                messages.error(request, "Nome do professor não confere com o cadastro deste curso.")
            return redirect('cursos:chamada_publica', token=token)

        # LÓGICA DE LOGOUT
        if action == 'logout':
            if auth_key in request.session:
                del request.session[auth_key]
            return redirect('cursos:chamada_publica', token=token)

        # LÓGICA DE SALVAR CHAMADA (EXISTENTE)
        if action == 'salvar_chamada':
            if not request.session.get(auth_key):
                return redirect('cursos:chamada_publica', token=token)

            hoje = date.today()
            ids_presentes = request.POST.getlist('presencas')
            registro, _ = RegistroAula.objects.get_or_create(curso=curso, data_aula=hoje)
            inscricoes = Inscricao.objects.filter(curso=curso, status='cursando')
            
            for insc in inscricoes:
                status = 'P' if str(insc.id) in ids_presentes else 'A'
                Chamada.objects.update_or_create(
                    registro_aula=registro,
                    inscricao=insc,
                    defaults={'status_presenca': status}
                )
                
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"school_notifications_{curso.escola.id}",
                    {
                        "type": "send_notification",
                        "message": f"Chamada realizada: {curso.nome} ({curso.turno})",
                        "notification_type": "success",
                    }
                )
            except Exception as e:
                print(f"Erro ao enviar notificação WebSocket: {e}")
                
            messages.success(request, f"Chamada de {curso.nome} salva com sucesso para {hoje.strftime('%d/%m/%Y')}!")
            return redirect('cursos:chamada_publica', token=token)
            
        return redirect('cursos:chamada_publica', token=token)
     
        messages.success(request, f"Chamada de {curso.nome} salva com sucesso para {hoje.strftime('%d/%m/%Y')}!")
        return redirect('cursos:chamada_publica', token=token)

class RegenerarTokensView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View administrativa para corrigir duplicatas de token_acesso no banco de dados.
    Utilizada para garantir a integridade dos links de chamada pública.
    """
    def test_func(self):
        return self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        import uuid
        from django.db import transaction
        
        cursos = Curso.objects.all()
        tokens_seen = set()
        fix_count = 0
        total_count = cursos.count()
        
        with transaction.atomic():
            for curso in cursos:
                # Se o token for nulo, vazio ou já tiver sido visto, gera um novo
                if not curso.token_acesso or str(curso.token_acesso) in tokens_seen:
                    new_token = uuid.uuid4()
                    # Garante que o novo token também não exista no banco
                    while Curso.objects.filter(token_acesso=new_token).exists():
                        new_token = uuid.uuid4()
                    
                    curso.token_acesso = new_token
                    curso.save()
                    fix_count += 1
                
                tokens_seen.add(str(curso.token_acesso))
        
        messages.success(request, f"Processamento concluído: {total_count} cursos verificados, {fix_count} códigos (tokens) corrigidos.")
        return redirect('cursos:lista_cursos')

# --- CRUD para Parceiro ---

class ParceiroListView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = Parceiro
    template_name = 'cursos/parceiro_list.html'
    context_object_name = 'parceiros'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Parceiro.objects.all().order_by('escola__nome', 'nome')
        if hasattr(user, 'profile') and user.profile.escola:
            return Parceiro.objects.filter(escola=user.profile.escola).order_by('nome')
        return Parceiro.objects.none()

class ParceiroCreateView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, CreateView):
    model = Parceiro
    form_class = ParceiroForm
    template_name = 'cursos/parceiro_form.html'
    success_url = reverse_lazy('cursos:lista_parceiros')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class ParceiroDeleteView(LoginRequiredMixin, StaffRequiredMixin, AuditLogMixin, DeleteView):
    model = Parceiro
    template_name = 'cursos/curso_confirm_delete.html' 
    success_url = reverse_lazy('cursos:lista_parceiros')

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

class CursoAvaliacaoDashboardView(LoginRequiredMixin, StaffRequiredMixin, DetailView):
    model = Curso
    template_name = 'cursos/avaliacao_dashboard.html'
    context_object_name = 'curso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.object
        inscricoes_concluidas = curso.inscricao_set.filter(status='concluido').select_related('aluno')
        total_concluintes = inscricoes_concluidas.count()
        avaliacoes_prof = AvaliacaoProfessorAluno.objects.filter(inscricao__curso=curso).count()
        avaliacoes_aluno = AvaliacaoAlunoCurso.objects.filter(inscricao__curso=curso).count()
        context['inscricoes'] = inscricoes_concluidas
        context['total_concluintes'] = total_concluintes
        context['avaliacoes_prof_count'] = avaliacoes_prof
        context['avaliacoes_aluno_count'] = avaliacoes_aluno
        context['perc_prof'] = int((avaliacoes_prof / total_concluintes * 100)) if total_concluintes > 0 else 0
        context['perc_aluno'] = int((avaliacoes_aluno / total_concluintes * 100)) if total_concluintes > 0 else 0
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
        concluintes = curso.inscricao_set.filter(status='concluido').select_related('aluno').prefetch_related('avaliacao_professor')
        return render(request, self.template_name, {'curso': curso, 'concluintes': concluintes, 'hide_navbar': True})

class AvaliarEstudanteAjaxView(View):
    def get(self, request, inscricao_pk):
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
        instance = getattr(inscricao, 'avaliacao_professor', None)
        from .forms import AvaliacaoProfessorAlunoForm
        form = AvaliacaoProfessorAlunoForm(instance=instance)
        return render(request, 'cursos/avaliacao_professor_modal_content.html', {'form': form, 'inscricao': inscricao})
    def post(self, request, inscricao_pk):
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
        instance = getattr(inscricao, 'avaliacao_professor', None)
        from .forms import AvaliacaoProfessorAlunoForm
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
        from .models import Inscricao
        inscricao = Inscricao.objects.filter(curso=curso, status='concluido', aluno__cpf__icontains=cpf_limpo).first()
        if not inscricao:
            from django.contrib import messages
            messages.error(request, 'CPF nao encontrado entre os alunos concluintes deste curso.')
            return redirect(reverse('cursos:avaliar_curso_publico', kwargs={'token': token}))
        if hasattr(inscricao, 'avaliacao_aluno'):
            return render(request, 'cursos/avaliacao_aluno_concluida.html', {'curso': curso, 'aluno': inscricao.aluno, 'hide_navbar': True})
        from .forms import AvaliacaoAlunoCursoForm
        form = AvaliacaoAlunoCursoForm()
        return render(request, self.template_name, {'curso': curso, 'aluno': inscricao.aluno, 'form': form, 'cpf': cpf, 'hide_navbar': True})
    def post(self, request, token):
        curso = get_object_or_404(Curso, token_acesso=token)
        cpf = request.POST.get('cpf')
        import re
        cpf_limpo = re.sub(r'\D', '', cpf)
        from .models import Inscricao
        inscricao = get_object_or_404(Inscricao, curso=curso, status='concluido', aluno__cpf__icontains=cpf_limpo)
        from .forms import AvaliacaoAlunoCursoForm
        form = AvaliacaoAlunoCursoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.inscricao = inscricao
            avaliacao.save()
            return render(request, 'cursos/avaliacao_aluno_concluida.html', {'curso': curso, 'aluno': inscricao.aluno, 'sucesso': True, 'hide_navbar': True})
        return render(request, self.template_name, {'curso': curso, 'aluno': inscricao.aluno, 'form': form, 'cpf': cpf, 'hide_navbar': True})

class ObterDadosGraficosAvaliacaoView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, pk):
        curso = get_object_or_404(Curso, pk=pk)
        from .models import AvaliacaoAlunoCurso
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
        inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
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
        curso = get_object_or_404(Curso, pk=pk)
        from .models import AvaliacaoProfessorAluno, AvaliacaoAlunoCurso
        
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
        curso = get_object_or_404(Curso, pk=pk)
        data_selecionada = request.GET.get('data')
        
        chamadas = None
        if data_selecionada:
            # Encontrar registro de aula para esta data
            registro = RegistroAula.objects.filter(curso=curso, data_aula=data_selecionada).first()
            if registro:
                chamadas = Chamada.objects.filter(registro_aula=registro, status_presenca__in=['A', 'J'])
            else:
                messages.warning(request, f"Nenhum registro de aula encontrado para a data {data_selecionada}.")

        return render(request, self.template_name, {
            'curso': curso,
            'chamadas': chamadas,
            'data_selecionada': data_selecionada,
            'motivos': Chamada.MOTIVO_FALTA_CHOICES
        })

    def post(self, request, pk):
        curso = get_object_or_404(Curso, pk=pk)
        chamadas_ids = request.POST.getlist('chamada_id')
        data_aula = request.POST.get('data_aula')
        
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

        messages.success(request, "Motivos de falta atualizados com sucesso.")
        return redirect(reverse('cursos:curso_qualitativos', kwargs={'pk': pk}) + f"?data={data_aula}")
