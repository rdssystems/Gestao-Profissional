from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from datetime import date
from django.db.models import Sum, Q # Importando Sum e Q

from .models import ControleDiario, RelatorioDiarioSine
from .forms import ControleDiarioForm, RelatorioDiarioSineForm
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
@user_passes_test(lambda u: u.is_superuser or (hasattr(u, 'profile') and u.profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH'])) # Superusuários e Administradores de Segmento
def controle_diario_admin_view(request):
    sistema = request.session.get('sistema', 'cp').upper()
    data_selecionada_str = request.GET.get('data')
    escola_id = request.GET.get('escola')
    
    hoje = date.today()
    try:
        data_selecionada = date.fromisoformat(data_selecionada_str) if data_selecionada_str else hoje
    except ValueError:
        messages.error(request, "Formato de data inválido. Usando a data atual.")
        data_selecionada = hoje

    # Filtro base para os dados individuais
    if request.user.is_superuser:
        controles_diarios_qs = ControleDiario.objects.filter(data=data_selecionada).select_related('escola', 'usuario')
        todas_escolas = Escola.objects.all().order_by('tipo', 'nome')
    else:
        controles_diarios_qs = ControleDiario.objects.filter(data=data_selecionada, escola__tipo=sistema).select_related('escola', 'usuario')
        todas_escolas = Escola.objects.filter(tipo=sistema).order_by('nome')

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

    # Buscar dados do SINE para a data - so pra admin de verdade (nao
    # admin_cp/admin_uditech, que tambem passam no @user_passes_test acima
    # mas nao devem ver indicadores do SINE).
    is_super_admin = request.user.is_superuser or (
        hasattr(request.user, 'profile') and request.user.profile.nivel_acesso == 'SUPERUSER'
    )
    sine_relatorio = RelatorioDiarioSine.objects.filter(data=data_selecionada).first() if is_super_admin else None

    # Dados pre-calculados pro Dashboard v2 (barras/ranking em CSS puro,
    # sem Chart.js): percentuais prontos do Python, igual ao redesign do
    # Dashboard principal (escolas/views.py) — mesmo motivo: menos JS, mais
    # facil de ler com poucas ou muitas unidades, sem estourar a paleta de
    # cores fixa que o donut antigo usava (só 6 cores pra ate 9 fatias).
    controles_list = list(controles_diarios_qs)
    max_val_principal = max(
        [max(c.atendimento, c.inscricoes) for c in controles_list], default=0
    )
    max_val_telecom = max(
        [max(c.ligacoes_recebidas, c.ligacoes_realizadas) for c in controles_list], default=0
    )
    total_inscricoes_impacto = sum(c.inscricoes for c in controles_list)

    def pct(numerador, denominador):
        return int((numerador / denominador) * 100) if denominador else 0

    unidades_chart = [
        {
            'nome': c.escola.nome,
            'atendimento': c.atendimento,
            'atendimento_pct': pct(c.atendimento, max_val_principal),
            'inscricoes': c.inscricoes,
            'inscricoes_pct': pct(c.inscricoes, max_val_principal),
            'impacto_pct': pct(c.inscricoes, total_inscricoes_impacto),
            'lig_recebidas': c.ligacoes_recebidas,
            'lig_recebidas_pct': pct(c.ligacoes_recebidas, max_val_telecom),
            'lig_realizadas': c.ligacoes_realizadas,
            'lig_realizadas_pct': pct(c.ligacoes_realizadas, max_val_telecom),
        }
        for c in controles_list
    ]
    unidades_impacto_ordenado = sorted(unidades_chart, key=lambda u: u['inscricoes'], reverse=True)

    context = {
        'controles_diarios': controles_diarios_qs,
        'totais': totais,
        'data_selecionada': data_selecionada,
        'escola_id_selecionada': escola_id,
        'todas_escolas': todas_escolas,
        'sine_relatorio': sine_relatorio,
        'unidades_chart': unidades_chart,
        'unidades_impacto_ordenado': unidades_impacto_ordenado,
    }
    return render(request, 'controle_diario/controle_diario_admin.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser or u.has_perm('controle_diario.add_relatoriodiariosine') or u.groups.filter(name='SINE').exists())
def preencher_relatorio_sine_view(request):
    hoje = date.today()
    instance = RelatorioDiarioSine.objects.filter(data=hoje).first()

    if request.method == 'POST':
        form = RelatorioDiarioSineForm(request.POST, instance=instance)
        if form.is_valid():
            relatorio = form.save(commit=False)
            relatorio.data = hoje
            relatorio.usuario = request.user
            relatorio.save()
            messages.success(request, "Indicadores diários do SINE salvos com sucesso!")
            return redirect('controle_diario:preencher_sine')
        else:
            messages.error(request, "Erro ao salvar os dados. Verifique os valores informados.")
    else:
        form = RelatorioDiarioSineForm(instance=instance)

    return render(request, 'controle_diario/preencher_sine.html', {
        'form': form,
        'hoje': hoje,
        'instance': instance,
        'hide_navbar': True,
    })