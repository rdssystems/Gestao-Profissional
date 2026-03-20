from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import date
from django.db.models import Sum, Q # Importando Sum e Q

from .models import ControleDiario
from .forms import ControleDiarioForm
from escolas.models import Escola

# Decorador para verificar se o usuário é superusuário OU tem perfil com escola
def can_access_controle_diario(user):
    return user.is_superuser or (hasattr(user, 'profile') and user.profile.escola)

@login_required
@user_passes_test(can_access_controle_diario)
def preencher_controle_diario_view(request):
    hoje = date.today()
    escola = None
    initial_data = {'data': hoje}

    if not request.user.is_superuser:
        if hasattr(request.user, 'profile') and request.user.profile.escola:
            escola = request.user.profile.escola
        else:
            messages.error(request, "Seu usuário não está vinculado a uma escola para preencher o Controle Diário.")
            return redirect('escolas:dashboard') # Ou outra página apropriada

    # Tenta carregar um registro existente para a data e escola
    instance = None
    if escola:
        instance = ControleDiario.objects.filter(escola=escola, data=hoje).first()

    if request.method == 'POST':
        if instance:
            messages.warning(request, "O controle diário para hoje já foi preenchido.")
            return redirect('controle_diario:preencher')

        form = ControleDiarioForm(request.POST)
        if form.is_valid():
            controle_diario = form.save(commit=False)
            controle_diario.data = hoje
            controle_diario.usuario = request.user
            if escola:
                controle_diario.escola = escola
            elif request.user.is_superuser:
                messages.error(request, "Superusuários devem usar o Admin para gerenciar controles diários.")
                return render(request, 'controle_diario/preencher_controle_diario.html', {'form': form, 'hoje': hoje})
            
            controle_diario.save()
            messages.success(request, "Controle Diário salvo com sucesso!")
            return redirect('controle_diario:preencher')
        else:
            messages.error(request, "Erro ao salvar. Verique os dados.")
    else:
        form = ControleDiarioForm(instance=instance, initial=initial_data)

    return render(request, 'controle_diario/preencher_controle_diario.html', {
        'form': form, 
        'hoje': hoje, 
        'escola': escola,
        'ja_enviado': True if instance else False
    })

@login_required
@user_passes_test(lambda u: u.is_superuser) # Apenas superusuários
def controle_diario_admin_view(request):
    data_selecionada_str = request.GET.get('data')
    escola_id = request.GET.get('escola')
    
    hoje = date.today()
    try:
        data_selecionada = date.fromisoformat(data_selecionada_str) if data_selecionada_str else hoje
    except ValueError:
        messages.error(request, "Formato de data inválido. Usando a data atual.")
        data_selecionada = hoje

    # Filtro base para os dados individuais
    controles_diarios_qs = ControleDiario.objects.filter(data=data_selecionada).select_related('escola', 'usuario')

    # Aplicar filtro de escola se fornecido
    if escola_id:
        controles_diarios_qs = controles_diarios_qs.filter(escola_id=escola_id)

    # Calcular totais somados
    totais = controles_diarios_qs.aggregate(
        total_atendimento=Sum('atendimento'),
        total_inscricoes=Sum('inscricoes'),
        total_pessoas_presentes=Sum('pessoas_presentes'),
        total_ligacoes_recebidas=Sum('ligacoes_recebidas'),
        total_ligacoes_realizadas=Sum('ligacoes_realizadas'),
    )

    context = {
        'controles_diarios': controles_diarios_qs,
        'totais': totais,
        'data_selecionada': data_selecionada,
        'escola_id_selecionada': escola_id,
        'todas_escolas': Escola.objects.all().order_by('nome'), # Para o filtro de escola
    }
    return render(request, 'controle_diario/controle_diario_admin.html', context)