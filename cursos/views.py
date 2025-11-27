import csv
import io
from datetime import date, time, datetime # Import datetime and time

from django.views.generic import ListView, DetailView, View
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import SingleObjectMixin
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin # Import UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render # Adicionar render aqui
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError 
from django import forms
from django.forms import inlineformset_factory # Adicionar import

# Importar modelos e formulários
from .models import Curso, TipoCurso, Inscricao, RegistroAula, Chamada # Adicionar RegistroAula, Chamada
from .forms import CursoForm, InscricaoForm, RegistroAulaForm, ChamadaFormSet, CursoCSVUploadForm, ChamadaForm # Adicionar RegistroAulaForm, ChamadaFormSet, CursoCSVUploadForm
from core.mixins import StaffRequiredMixin
from alunos.models import Aluno
from .validators import validar_conflito_matricula 

from escolas.models import Escola
# from datetime import date # Para usar date.today()


# Formulário para TipoCurso
class TipoCursoForm(forms.ModelForm):
    class Meta:
        model = TipoCurso
        fields = ['escola', 'nome', 'cor']

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
            return base_queryset
        
        if hasattr(user, 'profile') and user.profile.escola:
            return base_queryset.filter(escola=user.profile.escola)
        
        return base_queryset.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pega o queryset filtrado pelo get_queryset
        all_cursos = self.get_queryset()

        # Separa os cursos em ativos e concluídos
        context['cursos_ativos'] = all_cursos.filter(status__in=['Aberta', 'Em Andamento'])
        context['cursos_concluidos'] = all_cursos.filter(status='Concluído')

        # Adiciona os tipos de curso ao contexto, como antes
        user = self.request.user
        if user.is_superuser:
            context['tipos_curso'] = TipoCurso.objects.all()
        elif hasattr(user, 'profile') and user.profile.escola:
            context['tipos_curso'] = TipoCurso.objects.filter(escola=user.profile.escola)
        else:
            context['tipos_curso'] = TipoCurso.objects.none()
            
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

class CursoCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
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

class CursoUpdateView(StaffRequiredMixin, UpdateView):
    model = Curso
    form_class = CursoForm
    template_name = 'cursos/curso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class CursoDeleteView(StaffRequiredMixin, DeleteView):
    model = Curso
    template_name = 'cursos/curso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_cursos')

class CursoStatusUpdateView(LoginRequiredMixin, StaffRequiredMixin, View):
    model = Curso
    def post(self, request, pk):
        curso = get_object_or_404(Curso, pk=pk)
        novo_status = request.POST.get('status')
        if novo_status in [choice[0] for choice in Curso.STATUS_CHOICES]:
            curso.status = novo_status
            curso.save()
        return redirect('cursos:detalhe_curso', pk=pk)

# Views para TipoCurso
class TipoCursoListView(LoginRequiredMixin, ListView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_list.html'
    context_object_name = 'tipos_curso'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return TipoCurso.objects.all()
        
        if hasattr(user, 'profile') and user.profile.escola:
            return TipoCurso.objects.filter(escola=user.profile.escola)
        
        return TipoCurso.objects.none()

class TipoCursoCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'cursos/tipocurso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if not self.request.user.is_superuser:
            form.instance.escola = self.request.user.profile.escola
        return super().form_valid(form)

class TipoCursoUpdateView(StaffRequiredMixin, UpdateView):
    model = TipoCurso
    form_class = TipoCursoForm
    template_name = 'cursos/tipocurso_form.html'
    success_url = reverse_lazy('cursos:lista_cursos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class TipoCursoDeleteView(StaffRequiredMixin, DeleteView):
    model = TipoCurso
    template_name = 'cursos/tipocurso_confirm_delete.html'
    success_url = reverse_lazy('cursos:lista_cursos')

# Views para Inscrição
class InscricaoCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
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
        
        if curso.status != 'Aberta':
            messages.error(self.request, f'Não é possível inscrever alunos no curso {curso.nome} pois o status não é "Aberta".')
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
        if novo_status in ['concluido', 'desistente']:
            inscricao.status = novo_status
            inscricao.save()
            messages.success(request, f"Status do aluno '{inscricao.aluno.nome_completo}' atualizado para '{inscricao.get_status_display()}'.")
        else:
            messages.error(request, "Status inválido.")
            
        return redirect('cursos:detalhe_curso', pk=inscricao.curso.pk)

class MatriculaView(LoginRequiredMixin, ListView):
    model = Aluno
    template_name = 'cursos/matricula_page.html'
    context_object_name = 'alunos_sugeridos'

    def get_queryset(self):
        curso_id = self.request.GET.get('curso_id')
        if not curso_id:
            return Aluno.objects.none()

        curso = get_object_or_404(Curso, pk=curso_id, status='Aberta')
        
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
        
        # Queryset de cursos abertos para o seletor
        cursos_abertos_qs = Curso.objects.filter(status='Aberta')
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
        redirect_url = reverse_lazy('cursos:matricula') + f'?curso_id={curso_id}'

        

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



        # Cria a inscrição

        Inscricao.objects.create(aluno=aluno, curso=curso)

        messages.success(request, f'Aluno {aluno.nome_completo} matriculado com sucesso no curso {curso.nome}.')

        return redirect(redirect_url)
class InscricaoDeleteView(LoginRequiredMixin, StaffRequiredMixin, DeleteView):
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
            form = RegistroAulaForm(instance=registro_aula)
        else:
            # Tentar encontrar um registro de aula para hoje para este curso
            registro_aula = RegistroAula.objects.filter(curso=curso, data_aula=date.today()).first()
            if registro_aula:
                form = RegistroAulaForm(instance=registro_aula)
                messages.info(request, f"Já existe um registro de aula para {curso.nome} em {date.today().strftime('%d/%m/%Y')}. Editando o registro existente.")
            else:
                form = RegistroAulaForm(initial={'curso': curso, 'data_aula': date.today()})

        # Filtrar inscrições ativas para o curso
        # Não precisamos mais do queryset de inscrições aqui diretamente, o formset já fará isso
        # ou se formarmos o formset com base em inscricoes, ele as usará.
        
        # Definir formset inicial (para registros existentes ou vazio)
        # IMPORTANTE: Usar sempre prefix='chamada' para consistência com o POST e o formulário dinâmico
        if registro_aula:
             formset = ChamadaFormSet(instance=registro_aula, prefix='chamada')
        else:
             formset = ChamadaFormSet(instance=None, prefix='chamada') # Inicializa vazio se não houver registro, será substituído abaixo se for criação

        # Se for um novo registro de aula e o formset estiver vazio, pré-popular com os alunos cursando
        if registro_aula is None and not formset.is_bound and not request.POST:
            inscricoes_cursando = Inscricao.objects.filter(curso=curso, status='cursando')
            initial_chamadas = []
            for inscricao in inscricoes_cursando:
                initial_chamadas.append({'inscricao': inscricao, 'status_presenca': 'A'})
            
            # Dinamicamente criar o formset com o número correto de extras para exibir os alunos
            ChamadaFormSetDynamic = inlineformset_factory(
                RegistroAula, 
                Chamada, 
                form=ChamadaForm, 
                extra=len(initial_chamadas), 
                can_delete=False, 
                fields=['inscricao', 'status_presenca']
            )
            formset = ChamadaFormSetDynamic(initial=initial_chamadas, prefix='chamada')
            
            # Para o ChamadaForm, precisamos garantir que o aluno_nome é exibido mesmo no initial
            for f in formset:
                if f.initial and f.initial.get('inscricao'):
                    f.fields['aluno_nome'].initial = f.initial['inscricao'].aluno.nome_completo
        else:
             # Para chamadas existentes ou formset após POST, garantir que aluno_nome é exibido
            for f in formset:
                if f.instance.pk: # Se é uma instância existente de Chamada
                    f.fields['aluno_nome'].initial = f.instance.inscricao.aluno.nome_completo
                elif f.initial and f.initial.get('inscricao'): # Para forms com initial data após POST inválido
                    f.fields['aluno_nome'].initial = f.initial['inscricao'].aluno.nome_completo


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

        registro_aula = None
        if registro_aula_pk:
            registro_aula = get_object_or_404(RegistroAula, pk=registro_aula_pk, curso=curso)
            
        form = RegistroAulaForm(request.POST, instance=registro_aula)
        
        # Passar a instância corretamente para o formset para que ele saiba qual RegistroAula está sendo modificado
        # IMPORTANTE: Usar prefix='chamada' para corresponder ao que foi gerado no GET (seja dinâmico ou não)
        formset = ChamadaFormSet(request.POST, instance=registro_aula, prefix='chamada') 

        if form.is_valid() and formset.is_valid():
            registro_aula_instance = form.save(commit=False)
            registro_aula_instance.curso = curso # Garante que o curso está atribuído
            registro_aula_instance.save() # Salva o RegistroAula antes de salvar o formset

            # Salvar o formset, que agora tem a instância pai (registro_aula_instance)
            # formset.save() # Isso salva todos os objetos Chamada relacionados ao RegistroAula
            
            # Percorrer o formset para garantir que `registro_aula` está setado e lidar com novas instâncias
            # E para garantir que a inscrição pertence ao curso correto
            for form_chamada in formset:
                if form_chamada.instance.pk: # Se é uma instância existente
                    form_chamada.save()
                elif form_chamada.has_changed(): # Se é uma nova instância e tem dados
                    chamada = form_chamada.save(commit=False)
                    chamada.registro_aula = registro_aula_instance
                    
                    # Garantir que a inscrição está presente (pode ter vindo do hidden field ou initial)
                    if not chamada.inscricao_id:
                         # Tenta pegar do cleaned_data se não estiver na instância (ex: campo hidden)
                         inscricao = form_chamada.cleaned_data.get('inscricao')
                         if inscricao:
                             chamada.inscricao = inscricao

                    # Validação adicional: A inscrição deve ser do curso correto
                    if chamada.inscricao and chamada.inscricao.curso == curso:
                        chamada.save()
                    else:
                        messages.error(request, f"Inscrição {chamada.inscricao.aluno.nome_completo} não pertence ao curso {curso.nome}.")
                        # Se houver um erro, precisamos renderizar o formulário novamente com os dados
                        # e a mensagem de erro.
                        context = {
                            'curso': curso,
                            'form': form,
                            'formset': formset,
                            'registro_aula': registro_aula_instance,
                        }
                        return render(request, self.template_name, context)

            messages.success(request, f"Chamada para o curso '{curso.nome}' em {registro_aula_instance.data_aula.strftime('%d/%m/%Y')} salva com sucesso!")
            # Redireciona para a edição do mesmo RegistroAula
            return redirect('cursos:fazer_chamada_editar', curso_pk=curso.pk, registro_aula_pk=registro_aula_instance.pk) 

        else:
            messages.error(request, "Houve um erro na submissão do formulário. Por favor, verifique os dados.")
            # Para o contexto, é importante ter o `aluno_nome` para os forms no formset
            for f in formset:
                # É importante re-preencher 'aluno_nome' se o formset falhou na validação
                # Verifica se a instância tem um ID (existe no banco) ou se tem a relação 'inscricao' setada
                if f.instance.pk and hasattr(f.instance, 'inscricao'):
                    f.fields['aluno_nome'].initial = f.instance.inscricao.aluno.nome_completo
                elif f.cleaned_data and f.cleaned_data.get('inscricao'): # Se os dados limpos tem a inscrição
                     f.fields['aluno_nome'].initial = f.cleaned_data['inscricao'].aluno.nome_completo

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
    paginate_by = 10

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