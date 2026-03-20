from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

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


@login_required
def config_view(request):
    """Main WhatsApp configuration page."""
    escola = _get_escola_for_user(request.user)

    if request.user.is_superuser:
        # Superuser sees all escola configs
        configs = WhatsAppConfig.objects.select_related('escola').all().order_by('escola__nome')
        return render(request, 'whatsapp/config_admin.html', {'configs': configs})

    if not escola:
        messages.error(request, "Você não tem uma escola vinculada à sua conta.")
        return redirect('escolas:dashboard')

    config, created = WhatsAppConfig.objects.get_or_create(
        escola=escola,
        defaults={'instance_name': f"escola-{escola.id}"}
    )

    # Check live status from the API on page load
    live_status = services.get_instance_status(config.instance_name)
    if live_status:
        api_state = live_status.get('instance', {}).get('state', 'close')
        if api_state == 'open':
            new_status = 'connected'
        elif api_state in ['connecting', 'close']:
            new_status = 'connecting'
        else:
            new_status = 'disconnected'
            
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])
    else:
        # Instance doesn't exist on API
        if config.status != 'disconnected':
            config.status = 'disconnected'
            config.save(update_fields=['status'])

    return render(request, 'whatsapp/config.html', {'config': config, 'escola': escola})


@login_required
@require_POST
def create_instance_view(request):
    """Creates or reconnects a WhatsApp instance for the user's school."""
    escola = _get_escola_for_user(request.user)
    if not escola:
        messages.error(request, "Ação não permitida.")
        return redirect('whatsapp:config')

    config, _ = WhatsAppConfig.objects.get_or_create(
        escola=escola,
        defaults={'instance_name': f"escola-{escola.id}"}
    )

    try:
        services.create_instance(config.instance_name)
        config.status = 'connecting'
        config.save(update_fields=['status'])
        messages.success(request, "Instância criada! Carregue o QR Code para conectar.")
    except services.EvolutionAPIError as e:
        messages.error(request, f"Erro ao criar instância: {e}")

    return redirect('whatsapp:config')


@login_required
def get_qr_code_view(request):
    """Returns the QR code as a JSON response (for dynamic polling)."""
    escola = _get_escola_for_user(request.user)
    if not escola:
        return JsonResponse({'error': 'Sem escola vinculada.'}, status=403)

    config = get_object_or_404(WhatsAppConfig, escola=escola)

    try:
        result = services.get_qr_code(config.instance_name)
        qr_base64 = ""
        
        # Check v1 structure: result['qrcode']['base64']
        if isinstance(result, dict) and 'qrcode' in result:
            qr_base64 = result['qrcode'].get('base64', '')
        
        # Check v2/fallback structure: result['base64']
        if not qr_base64 and isinstance(result, dict):
            qr_base64 = result.get('base64', '')

        if qr_base64:
            # Make sure it has the data URI prefix
            if not qr_base64.startswith('data:'):
                qr_base64 = f"data:image/png;base64,{qr_base64}"
            return JsonResponse({'qr_code': qr_base64, 'status': 'ready'})
        else:
            return JsonResponse({'qr_code': None, 'status': 'not_ready'})
    except services.EvolutionAPIError as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def check_status_view(request):
    """Returns the current live status for the escola's WhatsApp instance."""
    escola = _get_escola_for_user(request.user)
    if not escola:
        return JsonResponse({'error': 'Sem escola vinculada.'}, status=403)

    config = get_object_or_404(WhatsAppConfig, escola=escola)

    live_status = services.get_instance_status(config.instance_name)
    if live_status:
        api_state = live_status.get('instance', {}).get('state', 'close')
        if api_state == 'open':
            new_status = 'connected'
        elif api_state in ['connecting', 'close']:
            new_status = 'connecting'
        else:
            new_status = 'disconnected'
        
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])
    else:
        # Instance doesn't exist on API
        new_status = 'disconnected'
        if config.status != new_status:
            config.status = new_status
            config.save(update_fields=['status'])

    return JsonResponse({'status': new_status, 'status_display': config.get_status_display()})


@login_required
@require_POST
def disconnect_view(request):
    """Disconnects and deletes the WhatsApp instance."""
    escola = _get_escola_for_user(request.user)
    if not escola:
        messages.error(request, "Ação não permitida.")
        return redirect('whatsapp:config')

    config = get_object_or_404(WhatsAppConfig, escola=escola)

    try:
        services.delete_instance(config.instance_name)
        config.status = 'disconnected'
        config.save(update_fields=['status'])
        messages.success(request, "WhatsApp desconectado com sucesso.")
    except services.EvolutionAPIError as e:
        messages.warning(request, f"Aviso ao desconectar: {e}")
        config.status = 'disconnected'
        config.save(update_fields=['status'])

    return redirect('whatsapp:config')
