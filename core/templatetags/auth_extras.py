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
    if user.groups.filter(name__in=['Coordenador', 'Auxiliar Administrativo']).exists():
        return False
    profile = getattr(user, 'profile', None)
    if profile and not profile.escola and profile.nivel_acesso in ['ADMIN_CP', 'ADMIN_UDITECH']:
        return True
    return False
