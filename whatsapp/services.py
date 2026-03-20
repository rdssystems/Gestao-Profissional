import requests
import os
import logging

logger = logging.getLogger(__name__)

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
        raise EvolutionAPIError("Não foi possível conectar à Evolution API. Verifique se o serviço está rodando.")
    except requests.exceptions.Timeout:
        raise EvolutionAPIError("A Evolution API não respondeu a tempo (timeout).")
    except requests.exceptions.HTTPError as e:
        error_body = e.response.text
        raise EvolutionAPIError(f"Erro HTTP {e.response.status_code}: {error_body}")


def create_instance(instance_name):
    """Creates a new WhatsApp instance on the Evolution API."""
    # First, try to delete existing instance if any (idempotent)
    try:
        _make_request('DELETE', f'/instance/delete/{instance_name}')
    except EvolutionAPIError:
        pass  # Instance didn't exist, that's fine

    data = {
        "instanceName": instance_name,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
    }
    return _make_request('POST', '/instance/create', data=data)


def get_qr_code(instance_name):
    """
    Fetches the current QR code for a given instance.
    Evolution API v1: GET /instance/connect/{name} can return the QR or connection info. 
    Alternatively, some v1 versions use /instance/qrcode/{name}.
    """
    try:
        # First try the qrcode endpoint (v1 specific)
        return _make_request('GET', f'/instance/qrcode/{instance_name}')
    except EvolutionAPIError:
        # Fallback to connect endpoint
        return _make_request('GET', f'/instance/connect/{instance_name}')


def get_pairing_code(instance_name, phone_number):
    """
    Note: Pairing codes are only available in Evolution API v2+. 
    Returning dummy or raising error for v1.
    """
    raise EvolutionAPIError("Códigos de pareamento via texto só estão disponíveis na Evolution API v2. Favor usar o QR Code.")


def get_instance_status(instance_name):
    """Checks the connection status of a given instance."""
    try:
        result = _make_request('GET', f'/instance/connectionState/{instance_name}')
        return result
    except EvolutionAPIError:
        return None


def delete_instance(instance_name):
    """Deletes a WhatsApp instance from the Evolution API."""
    return _make_request('DELETE', f'/instance/delete/{instance_name}')


def send_text_message(instance_name, phone_number, text):
    """
    Sends a text message via WhatsApp.
    phone_number should contain only digits, e.g. '5534997648892'
    """
    # Ensure the phone number has the country code
    if not phone_number.startswith('55'):
        phone_number = '55' + phone_number

    data = {
        "number": phone_number,
        "text": text,
    }
    return _make_request('POST', f'/message/sendText/{instance_name}', data=data)
