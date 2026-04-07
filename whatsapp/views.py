from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.urls import reverse

from escolas.models import Escola
from .models import WhatsAppConfig
from . import services


def _get_escola_for_user(user):
    """Returns the escola for the current user, or None if superuser."""
    if user.is_superuser:
        return None
    if hasattr(user, 'profile') and user.profile.escola:
        return user.profile.escola
    return None


def _get_config_and_escola(user, escola_id=None):
    """
    Helper to get the appropriate config and escola based on the user and an optional id.
    """
    if user.is_superuser and escola_id:
        escola = get_object_or_404(Escola, pk=escola_id)
    else:
        escola = _get_escola_for_user(user)
    
    if not escola:
        return None, None
        
    config, created = WhatsAppConfig.objects.get_or_create(
        escola=escola,
        defaults={'instance_name': f"escola-{escola.id}"}
    )
    return config, escola


@login_required
def config_view(request, escola_id=None):
    """Main WhatsApp configuration page."""
    # Superuser sees the global dashboard by default
    if request.user.is_superuser and not escola_id:
        configs = WhatsAppConfig.objects.select_related('escola').all().order_by('escola__nome')
        return render(request, 'whatsapp/config_admin.html', {'configs': configs})

    # Individual school config (accessible by coordinator or admin with escola_id)
    config, escola = _get_config_and_escola(request.user, escola_id)
    if not escola:
        messages.error(request, "Ação não permitida ou escola não vinculada.")
        return redirect('escolas:dashboard')

    # Status check
    live_status = services.get_instance_status(config.instance_name)
    if live_status:
        api_state = live_status.get('instance', {}).get('state', 'close')
        new_status = 'connected' if api_state == 'open' else ('connecting' if api_state in ['connecting', 'close'] else 'disconnected')
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])
    else:
        if config.status != 'disconnected':
            config.status = 'disconnected'
            config.save(update_fields=['status'])

    # Prepare dynamic URLs for the template
    if request.user.is_superuser and escola_id:
        qr_code_url = reverse('whatsapp:qr_code_escola', kwargs={'escola_id': escola_id})
        status_url = reverse('whatsapp:check_status_escola', kwargs={'escola_id': escola_id})
        disconnect_url = reverse('whatsapp:desconectar_escola', kwargs={'escola_id': escola_id})
        create_url = reverse('whatsapp:criar_instancia_escola', kwargs={'escola_id': escola_id})
    else:
        qr_code_url = reverse('whatsapp:qr_code')
        status_url = reverse('whatsapp:check_status')
        disconnect_url = reverse('whatsapp:desconectar')
        create_url = reverse('whatsapp:criar_instancia')

    return render(request, 'whatsapp/config.html', {
        'config': config, 
        'escola': escola,
        'qr_code_url': qr_code_url,
        'status_url': status_url,
        'disconnect_url': disconnect_url,
        'create_url': create_url,
        'is_admin_managing': (request.user.is_superuser and escola_id is not None)
    })


@login_required
@require_POST
def create_instance_view(request, escola_id=None):
    config, escola = _get_config_and_escola(request.user, escola_id)
    if not escola:
        messages.error(request, "Erro ao identificar unidade.")
        return redirect('whatsapp:config')

    try:
        services.create_instance(config.instance_name)
        config.status = 'connecting'
        config.save(update_fields=['status'])
        messages.success(request, f"Iniciando conexão para {escola.nome}...")
    except services.EvolutionAPIError as e:
        messages.error(request, f"Erro: {e}")

    if request.user.is_superuser and escola_id:
        return redirect('whatsapp:config_escola', escola_id=escola_id)
    return redirect('whatsapp:config')


@login_required
def get_qr_code_view(request, escola_id=None):
    config, escola = _get_config_and_escola(request.user, escola_id)
    if not escola:
         return JsonResponse({'error': True, 'message': 'Acesso negado.'}, status=403)

    try:
        result = services.get_qr_code(config.instance_name)
        qr_base64 = ""
        if isinstance(result, dict):
            qr_base64 = result.get('qrcode', {}).get('base64', '') or result.get('base64', '')

        if qr_base64:
            if not qr_base64.startswith('data:'):
                qr_base64 = f"data:image/png;base64,{qr_base64}"
            return JsonResponse({'qr_code': qr_base64, 'status': 'ready'})
        return JsonResponse({'qr_code': None, 'status': 'not_ready'})
    except services.EvolutionAPIError as e:
        return JsonResponse({'error': True, 'message': str(e), 'status': 'error'})


@login_required
def check_status_view(request, escola_id=None):
    config, escola = _get_config_and_escola(request.user, escola_id)
    if not escola:
         return JsonResponse({'error': True, 'message': 'Erro.'}, status=403)

    live_status = services.get_instance_status(config.instance_name)
    if live_status:
        api_state = live_status.get('instance', {}).get('state', 'close')
        new_status = 'connected' if api_state == 'open' else ('connecting' if api_state in ['connecting', 'close'] else 'disconnected')
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])
    else:
        new_status = 'disconnected'
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])

    return JsonResponse({'status': new_status, 'status_display': config.get_status_display()})


@login_required
@require_POST
def disconnect_view(request, escola_id=None):
    config, escola = _get_config_and_escola(request.user, escola_id)
    if not escola:
        return redirect('whatsapp:config')

    try:
        services.delete_instance(config.instance_name)
        config.status = 'disconnected'
        config.save(update_fields=['status'])
        messages.success(request, f"WhatsApp da unidade {escola.nome} desconectado.")
    except services.EvolutionAPIError as e:
        config.status = 'disconnected'
        config.save(update_fields=['status'])
        messages.warning(request, f"Desconectado localmente. API erro: {e}")

    if request.user.is_superuser and escola_id:
        return redirect('whatsapp:config_escola', escola_id=escola_id)
    return redirect('whatsapp:config')
