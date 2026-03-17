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

@register.filter
def nome_curto(nome_completo):
    if not nome_completo:
        return ""
    partes = nome_completo.split()
    if len(partes) <= 1:
        return nome_completo
    # Retorna primeiro e último nome
    return f"{partes[0]} {partes[-1]}"
