from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()

@register.filter(name='is_global_admin')
def is_global_admin(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    if profile and not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']:
        return True
    return False

@register.filter(name='is_super_admin')
def is_super_admin(user):
    """Admin de verdade (sem escopo de sistema) — diferente de is_global_admin,
    que apesar do nome inclui ADMIN_CP/ADMIN_UDITECH (admins de segmento)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.nivel_acesso == 'SUPERUSER')
