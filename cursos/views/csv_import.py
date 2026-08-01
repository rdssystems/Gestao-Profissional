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


class CursoCSVUploadView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'cursos/upload_cursos_csv.html'

    def test_func(self):
        return self.request.user.is_superuser

    def handle_uploaded_file(self, file, sistema):
        from django.db import transaction

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
                # Cada linha e um savepoint proprio: se a linha falhar no
                # meio (ex.: TipoCurso ja criado/atualizado, mas Curso falha
                # logo depois por carga_horaria invalida), desfaz só os
                # writes dessa linha — sem tornar o upload inteiro
                # tudo-ou-nada, o que mudaria o comportamento hoje (import
                # "melhor esforço": linha com erro é pulada e reportada, o
                # resto do arquivo continua).
                with transaction.atomic():
                    # 1. Get Escola by name (do not create if not found)
                    escola_nome = row.get('escola_nome')
                    if not escola_nome: # Validar campo obrigatório
                        raise ValueError("Coluna 'escola_nome' é obrigatória.")

                    try:
                        escola = Escola.objects.get(nome=escola_nome, tipo=sistema)
                    except Escola.DoesNotExist:
                        raise ValueError(f"Escola '{escola_nome}' não encontrada no portal ativo. As escolas devem ser criadas antes do upload do CSV.")

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

            sistema = request.session.get('sistema', 'cp').upper()
            created_count, updated_count, errors = self.handle_uploaded_file(csv_file, sistema)

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
