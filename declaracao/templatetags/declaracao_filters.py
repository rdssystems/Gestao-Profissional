from django import template
import re

register = template.Library()

@register.filter
def format_telefone(value):
    """
    Formata um número de telefone para (DD) NNNN-NNNN ou DD NNNNN-NNNN.
    Remove caracteres não numéricos antes de formatar.
    """
    if not value:
        return ""
    
    # Remove todos os caracteres não numéricos
    clean_number = re.sub(r'\D', '', str(value))

    # Formata de acordo com o comprimento
    if len(clean_number) == 10: # Ex: 3499998888
        return f"({clean_number[:2]}) {clean_number[2:6]}-{clean_number[6:]}"
    elif len(clean_number) == 11: # Ex: 34999998888
        return f"({clean_number[:2]}) {clean_number[2:7]}-{clean_number[7:]}"
    else:
        return value # Retorna o valor original se não puder formatar
