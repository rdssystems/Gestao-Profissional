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
    
    # Preposições comuns para nomes em português
    preps = ['de', 'da', 'do', 'das', 'dos', 'e']
    
    # Pegamos o primeiro nome
    primeiro = partes[0]
    
    # Verificamos se o segundo elemento é uma preposição
    if len(partes) > 2 and partes[1].lower() in preps:
        # Se for, combinamos Primeiro + Preposição + Próximo Nome
        return f"{primeiro} {partes[1]} {partes[2]}"
    
    # Caso contrário, apenas Primeiro + Segundo
    return f"{primeiro} {partes[1]}"

@register.filter
def apenas_numeros(valor):
    if not valor:
        return ""
    return "".join(filter(str.isdigit, str(valor)))
@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return int(int(value) / int(arg)) if int(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0
