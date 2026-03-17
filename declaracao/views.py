import base64
from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import translation
import os
import datetime
from django.conf import settings

from alunos.models import Aluno
from cursos.models import Inscricao
from alunos.forms import VerificarCPFForm
from .models import Declaracao
from .utils import get_aluno_status_para_inscricao, generate_declaration_text

@login_required
def buscar_aluno_view(request):
    if request.method == 'POST':
        form = VerificarCPFForm(request.POST)
        if form.is_valid():
            cpf = form.cleaned_data['cpf']
            cpf_digits = ''.join(filter(str.isdigit, cpf))
            
            # Start with all students
            alunos_query = Aluno.objects.filter(cpf=cpf_digits)

            # Filter by school if not superuser and has a profile with school
            if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola:
                alunos_query = alunos_query.filter(escola=request.user.profile.escola)

            aluno = alunos_query.first()

            if aluno:
                return redirect('declaracao:listar_cursos_aluno', aluno_id=aluno.id)
            else:
                messages.error(request, "Nenhum aluno encontrado com o CPF informado ou o aluno não pertence à sua escola.")
    else:
        form = VerificarCPFForm()
    
    return render(request, 'declaracao/buscar_aluno.html', {'form': form})

@login_required
def listar_cursos_view(request, aluno_id):
    aluno_query = Aluno.objects.filter(id=aluno_id)

    # Filter Aluno by school if not superuser
    if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola:
        aluno_query = aluno_query.filter(escola=request.user.profile.escola)
    
    aluno = get_object_or_404(aluno_query) # Use the filtered query

    # Filter inscricoes by school of the current user
    inscricoes = Inscricao.objects.filter(aluno=aluno).select_related('curso')
    if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola:
        inscricoes = inscricoes.filter(curso__escola=request.user.profile.escola)
    
    inscricoes = inscricoes.order_by('-curso__data_inicio')

    inscricoes_com_status = []
    for inscricao in inscricoes:
        status = get_aluno_status_para_inscricao(inscricao)
        # Include all inscriptions, but mark which ones can generate a declaration
        pode_gerar = status in ['matriculado', 'cursando', 'concluido']
        
        status_display_text = dict(Declaracao.STATUS_CHOICES).get(status)
        if not status_display_text:
             # Fallback for statuses not in the model choices (like 'aguardando_regularizacao')
             status_display_text = "Aguardando Regularização" if status == 'aguardando_regularizacao' else "Status Inválido"

        # Buscar histórico de declarações para esta inscrição
        historico = Declaracao.objects.filter(inscricao=inscricao).order_by('-data_emissao')

        inscricoes_com_status.append({
            'inscricao': inscricao,
            'status_display': status_display_text,
            'status_raw': status,
            'pode_gerar': pode_gerar,
            'historico': historico
        })

    return render(request, 'declaracao/listar_cursos.html', {
        'aluno': aluno,
        'inscricoes': inscricoes_com_status
    })

def _check_inscricao_permission(request, inscricao_id):
    inscricao = get_object_or_404(Inscricao, id=inscricao_id)

    # Check if not superuser and if the enrollment's course belongs to the user's school
    if not request.user.is_superuser and hasattr(request.user, 'profile') and request.user.profile.escola:
        if inscricao.curso.escola != request.user.profile.escola:
            messages.error(request, "Você não tem permissão para gerar declarações para esta inscrição.")
            # Redirect to the student's course list if permission is denied
            return None, redirect('declaracao:listar_cursos_aluno', aluno_id=inscricao.aluno.id)
    return inscricao, None # Return inscricao and no redirect if allowed

@login_required
def gerar_declaracao_view(request, inscricao_id, declaration_type=None): # Added declaration_type parameter
    inscricao, redirect_response = _check_inscricao_permission(request, inscricao_id)
    if redirect_response:
        return redirect_response

    original_status = get_aluno_status_para_inscricao(inscricao)
    status_for_declaration = original_status

    # If the original status is 'aguardando_regularizacao', allow override by declaration_type
    if original_status == 'aguardando_regularizacao':
        if declaration_type in ['matriculado', 'cursando']:
            status_for_declaration = declaration_type
        elif declaration_type: # Provided but invalid
            messages.error(request, f"Tipo de declaração inválido: {declaration_type}.")
            return redirect('declaracao:listar_cursos_aluno', aluno_id=inscricao.aluno.id)
        # If declaration_type is None, status_for_declaration remains 'aguardando_regularizacao'

    # Check if the chosen status (either original or overridden) is valid for declaration generation
    if status_for_declaration not in ['matriculado', 'cursando', 'concluido']:
        messages.error(request, f"Não é possível gerar uma declaração para esta inscrição (Status: {original_status}).")
        return redirect('declaracao:listar_cursos_aluno', aluno_id=inscricao.aluno.id)

    texto_declaracao = generate_declaration_text(status_for_declaration, inscricao)

    context = {
        'inscricao': inscricao,
        'texto': texto_declaracao,
        'status': status_for_declaration, # Use the potentially overridden status here
        'current_datetime': datetime.datetime.now(), # Pass current datetime for preview date
    }
    return render(request, 'declaracao/gerar_declaracao.html', context)

@login_required
def salvar_declaracao_view(request, inscricao_id):
    inscricao, redirect_response = _check_inscricao_permission(request, inscricao_id)
    if redirect_response:
        return redirect_response
    
    if request.method != 'POST':
        return redirect('declaracao:gerar_declaracao', inscricao_id=inscricao_id)

    status = get_aluno_status_para_inscricao(inscricao)
    
    if status not in ['matriculado', 'cursando', 'concluido']:
        messages.error(request, "O status da inscrição mudou e não permite mais a geração da declaração.")
        return redirect('declaracao:listar_cursos_aluno', aluno_id=inscricao.aluno.id)

    signature_base64 = request.POST.get('assinatura')
    
    if not signature_base64 or signature_base64 == 'data:,':
        messages.error(request, "A assinatura é obrigatória.")
        return redirect('declaracao:gerar_declaracao', inscricao_id=inscricao_id)

    texto_declaracao = generate_declaration_text(status, inscricao)

    declaracao = Declaracao.objects.create(
        inscricao=inscricao,
        emitido_por=request.user,
        texto=texto_declaracao,
        status_aplicado=status,
        assinatura_digital=signature_base64
    )
    
    return redirect('declaracao:declaracao_sucesso', declaracao_id=declaracao.id)

@login_required
def declaracao_sucesso_view(request, declaracao_id):
    declaracao = get_object_or_404(Declaracao, id=declaracao_id)
    return render(request, 'declaracao/declaracao_sucesso.html', {'declaracao': declaracao})


@login_required
def imprimir_declaracao_view(request, hash_validacao):
    declaracao = get_object_or_404(Declaracao, hash_validacao=hash_validacao)
    
    escola = declaracao.inscricao.aluno.escola # Get the school object
    
    context = {
        'declaracao': declaracao,
        'escola': escola, # Add school to context
    }
    return render(request, 'declaracao/declaracao_print.html', context)