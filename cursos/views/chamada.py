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
from core.utils import audit_context, save_audit_log

logger = logging.getLogger(__name__)
from alunos.models import Aluno
from ..validators import validar_conflito_matricula 

from escolas.models import Escola
# from datetime import date # Para usar date.today()


# Formulário para TipoCurso


class ChamadaCursoListView(LoginRequiredMixin, ListView):
    model = Curso
    template_name = 'cursos/lista_chamadas_cursos.html'
    context_object_name = 'cursos_para_chamada'
    
    def get_queryset(self):
        user = self.request.user
        sistema = self.request.session.get('sistema', 'cp').upper()
        queryset = Curso.objects.filter(status__in=['Aberta', 'Em Andamento'], escola__tipo=sistema) # Filtrar por status ativo

        active_escola = getattr(self.request, 'active_escola', None)
        if user.is_superuser:
            if active_escola:
                return queryset.filter(escola=active_escola)
            return queryset
        
        if active_escola:
            return queryset.filter(escola=active_escola)
        
        return Curso.objects.none()

# Nova View para Fazer/Editar Chamada

class FazerChamadaView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, View):
    template_name = 'cursos/fazer_chamada.html'

    def get(self, request, curso_pk, registro_aula_pk=None):
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=curso_pk, escola__tipo=sistema)
        
        # Verificar permissão de escola se não for superuser
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola and request.user.profile.escola != curso.escola and request.user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
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
        from django.db.models import Case, When, Value, IntegerField
        inscricoes_elegiveis = Inscricao.objects.filter(curso=curso, status__in=['cursando', 'desistente']).annotate(
            is_desistente=Case(
                When(status='desistente', then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by('is_desistente', 'aluno__nome_completo').select_related('aluno')
        
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
            from django.db.models import Case, When, Value, IntegerField
            formset.queryset = formset.queryset.annotate(
                is_desistente=Case(
                    When(inscricao__status='desistente', then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by('is_desistente', 'inscricao__aluno__nome_completo')
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
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=curso_pk, escola__tipo=sistema)

        # Verificar permissão de escola se não for superuser
        if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola and request.user.profile.escola != curso.escola and request.user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
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
            is_new_registro = registro_aula is None
            registro_aula_instance = form.save(commit=False)
            registro_aula_instance.curso = curso
            # RegistroAula esta na lista de models do core/audit_signals.py;
            # sem audit_context(skip=True) o post_save automatico gravaria
            # um log generico ALEM do log estruturado que fazemos abaixo
            # (mesmo bug corrigido em ExcluirRegistroAulaView).
            with audit_context(skip=True):
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

            # Log agregado (uma linha por submissão, não uma por aluno).
            chamadas_salvas = Chamada.objects.filter(registro_aula=registro_aula_instance)
            self.save_log(
                registro_aula_instance,
                'CREATE' if is_new_registro else 'UPDATE',
                {
                    'curso': curso.nome,
                    'data_aula': registro_aula_instance.data_aula.strftime('%d/%m/%Y'),
                    'presentes': chamadas_salvas.filter(status_presenca='P').count(),
                    'ausentes': chamadas_salvas.exclude(status_presenca='P').count(),
                },
            )

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
                    logger.warning("Erro ao repopular form #%s: %s", i, e)

            context = {
                'curso': curso,
                'form': form,
                'formset': formset,
                'registro_aula': registro_aula,
            }
            return render(request, self.template_name, context)

class ObterDadosChamadaDataView(LoginRequiredMixin, StaffRequiredMixin, View):
    def get(self, request, curso_pk):
        data_str = request.GET.get('data')
        if not data_str:
            return JsonResponse({'error': 'Data não fornecida'}, status=400)
        
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Formato de data inválido'}, status=400)
            
        sistema = request.session.get('sistema', 'cp').upper()
        curso = get_object_or_404(Curso, pk=curso_pk, escola__tipo=sistema)
        registro_aula = RegistroAula.objects.filter(curso=curso, data_aula=data_obj).first()
        
        if not registro_aula:
            return JsonResponse({'existe': False})
            
        chamadas = Chamada.objects.filter(registro_aula=registro_aula).values('inscricao_id', 'status_presenca')
        dados_chamada = {str(c['inscricao_id']): c['status_presenca'] for c in chamadas}
        
        return JsonResponse({
            'existe': True,
            'registro_aula_pk': registro_aula.pk,
            'observacoes': registro_aula.observacoes,
            'chamadas': dados_chamada
        })

class HistoricoChamadasCursoView(LoginRequiredMixin, StaffRequiredMixin, ListView):
    model = RegistroAula
    template_name = 'cursos/historico_chamadas_curso.html'
    context_object_name = 'registros_aula'
    paginate_by = 30 # Aumentado para ver mais dias

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        self.curso = get_object_or_404(Curso, pk=self.kwargs['curso_pk'], escola__tipo=sistema)
        
        # Verificar permissão de escola se não for superuser
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola and user.profile.escola != self.curso.escola and user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
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

    def get_queryset(self):
        sistema = self.request.session.get('sistema', 'cp').upper()
        return Curso.objects.filter(escola__tipo=sistema)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        return get_object_or_404(queryset, pk=self.kwargs['curso_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        curso = self.get_object()
        
        # Verificar permissão de escola
        user = self.request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola and user.profile.escola != curso.escola and user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
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
        
        # Verificar se está endo aberto no Modal
        if self.request.GET.get('modal') == '1':
            context['hide_navbar'] = True
            context['is_modal'] = True
            
        return context

class ExcluirRegistroAulaView(AuditLogMixin, LoginRequiredMixin, StaffRequiredMixin, View):
    def post(self, request, pk):
        sistema = request.session.get('sistema', 'cp').upper()
        registro = get_object_or_404(RegistroAula, pk=pk, curso__escola__tipo=sistema)
        curso = registro.curso
        
        # Verificar permissão de escola se não for superuser
        user = request.user
        if not user.is_superuser and hasattr(user, 'profile') and user.profile.escola and user.profile.escola != curso.escola and user.profile.nivel_acesso not in ['ADMIN_CP', 'ADMIN_UDITECH']:
            raise PermissionDenied("Você não tem permissão para excluir registros desta escola.")
            
        data_formatada = registro.data_aula.strftime('%d/%m/%Y')

        # Loga ANTES de deletar (registro.delete() zera o pk da instância).
        self.save_log(registro, 'DELETE', {'registro_aula_excluido': f"{data_formatada} - curso {curso.nome}"})

        # audit_context(skip=True): RegistroAula está na lista de models do
        # core/audit_signals.py — sem isso, o post_delete automático grava
        # um SEGUNDO log da mesma exclusão (bug corrigido em 2026-08-01).
        with audit_context(skip=True):
            registro.delete()

        messages.success(request, f"O registro de presença do dia {data_formatada} para o curso '{curso.nome}' foi removido com sucesso!")
        return redirect('cursos:relatorio_frequencia', curso_pk=curso.pk)

class ChamadaPublicaView(AuditLogMixin, View):
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
            # RegistroAula esta na lista de models do core/audit_signals.py;
            # skip=True evita um log generico duplicando o log estruturado
            # (com nome do professor) que gravamos logo abaixo.
            with audit_context(skip=True):
                registro, _ = RegistroAula.objects.get_or_create(curso=curso, data_aula=hoje)
            inscricoes = Inscricao.objects.filter(curso=curso, status='cursando')

            presentes_count = 0
            for insc in inscricoes:
                status = 'P' if str(insc.id) in ids_presentes else 'A'
                if status == 'P':
                    presentes_count += 1
                Chamada.objects.update_or_create(
                    registro_aula=registro,
                    inscricao=insc,
                    defaults={'status_presenca': status}
                )

            # Registro sem usuario autenticado (chamada via link publico
            # compartilhado com professor externo) — a unica rastreabilidade
            # disponivel e o nome do professor confirmado no login da pagina
            # e o IP, ambos capturados aqui.
            self.save_log(
                registro,
                'UPDATE',
                {
                    'curso': curso.nome,
                    'professor': curso.nome_professor,
                    'data_aula': hoje.strftime('%d/%m/%Y'),
                    'presentes': presentes_count,
                    'ausentes': inscricoes.count() - presentes_count,
                    'via': 'link publico (sem login de usuario)',
                },
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
                logger.warning("Erro ao enviar notificação WebSocket: %s", e)
                
            messages.success(request, f"Chamada de {curso.nome} salva com sucesso para {hoje.strftime('%d/%m/%Y')}!")
            return redirect('cursos:chamada_publica', token=token)
            
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
