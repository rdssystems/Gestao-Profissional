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
