import requests
import os
import logging

logger = logging.getLogger(__name__)

# Defaults for Docker environment
EVOLUTION_API_URL = os.getenv('EVOLUTION_API_URL', 'http://localhost:8080')
EVOLUTION_API_KEY = os.getenv('EVOLUTION_API_KEY', 'gq-evolution-secret-key-2026')

HEADERS = {
    'apikey': EVOLUTION_API_KEY,
    'Content-Type': 'application/json',
}


class EvolutionAPIError(Exception):
    pass


def _make_request(method, endpoint, data=None, timeout=10):
    """Generic helper to make requests to Evolution API."""
    url = f"{EVOLUTION_API_URL}{endpoint}"
    try:
        response = requests.request(method, url, headers=HEADERS, json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise EvolutionAPIError(f"Não foi possível conectar à Evolution API em {EVOLUTION_API_URL}. Verifique se o container docker 'gq-evolution' está rodando.")
    except requests.exceptions.Timeout:
        raise EvolutionAPIError("A Evolution API não respondeu a tempo (timeout).")
    except requests.exceptions.HTTPError as e:
        error_body = e.response.text
        raise EvolutionAPIError(f"Erro HTTP {e.response.status_code}: {error_body}")


def create_instance(instance_name):
    """Creates a new WhatsApp instance on the Evolution API. No pre-delete to avoid race conditions."""
    data = {
        "instanceName": instance_name,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
    }
    
    try:
        return _make_request('POST', '/instance/create', data=data)
    except EvolutionAPIError as e:
        # If the instance already exists, we skip creation and just return its current status
        if "already exists" in str(e).lower():
            logger.info(f"Instância {instance_name} já existe na API. Prosseguindo.")
            return get_instance_status(instance_name)
        raise e


def get_qr_code(instance_name):
    """Fetches the current QR code for a given instance with fallback endpoints."""
    try:
        # First try the qrcode endpoint (v1 specific)
        return _make_request('GET', f'/instance/qrcode/{instance_name}')
    except EvolutionAPIError:
        # Fallback to connect endpoint
        return _make_request('GET', f'/instance/connect/{instance_name}')


def get_instance_status(instance_name):
    """Checks the connection status of a given instance."""
    try:
        result = _make_request('GET', f'/instance/connectionState/{instance_name}')
        return result
    except EvolutionAPIError:
        return None


def delete_instance(instance_name):
    """Deletes a WhatsApp instance from the Evolution API."""
    try:
        return _make_request('DELETE', f'/instance/delete/{instance_name}')
    except EvolutionAPIError:
        # If it doesn't exist to delete, that's already what we wanted
        return {"status": "already_deleted"}


def send_text_message(instance_name, phone_number, text):
    """Sends a text message via WhatsApp."""
    if not phone_number.startswith('55'):
        phone_number = '55' + phone_number

    data = {
        "number": phone_number,
        "text": text,
    }
    return _make_request('POST', f'/message/sendText/{instance_name}', data=data)
