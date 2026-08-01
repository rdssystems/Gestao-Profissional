import threading
from contextlib import contextmanager

_thread_locals = threading.local()

def set_current_user(user):
    _thread_locals.user = user

def get_current_user():
    return getattr(_thread_locals, 'user', None)

def set_audit_skip(value):
    _thread_locals.audit_skip = value

def get_audit_skip():
    return getattr(_thread_locals, 'audit_skip', False)

@contextmanager
def audit_context(skip=True):
    old_value = get_audit_skip()
    set_audit_skip(skip)
    try:
        yield
    finally:
        set_audit_skip(old_value)

def normalize_name(name):
    if not name:
        return ""
    
    prepositions = ['de', 'da', 'do', 'das', 'dos', 'e']
    words = name.lower().split()
    normalized_words = []
    
    for i, word in enumerate(words):
        if word in prepositions and i > 0:
            normalized_words.append(word)
        else:
            normalized_words.append(word.capitalize())
            
    return " ".join(normalized_words)

def clean_digits(value):
    import re
    if not value:
        return ""
    return re.sub(r'\D', '', value)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def is_rate_limited(request, key, limit):
    """
    Throttle simples baseado em cache (Redis em produção, locmem em dev).
    Usado em endpoints sem nenhuma proteção contra força bruta/enumeração
    (login administrativo, busca de CPF no portal público).
    """
    from django.core.cache import cache
    ip = get_client_ip(request) or 'unknown'
    count = cache.get(f'throttle:{key}:{ip}', 0)
    return count >= limit


def register_attempt(request, key, window_seconds):
    """Incrementa o contador de tentativas usado por is_rate_limited."""
    from django.core.cache import cache
    ip = get_client_ip(request) or 'unknown'
    cache_key = f'throttle:{key}:{ip}'
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
