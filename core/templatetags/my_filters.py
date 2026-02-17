from django import template

register = template.Library()

@register.filter
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False

@register.filter
def can_access_controle_diario(user):
    # Retorna True se o usuário é superusuário OU se tem um perfil e esse perfil está associado a uma escola
    return user.is_superuser or (hasattr(user, 'profile') and user.profile and user.profile.escola)
