from django.contrib.auth.models import Group

def user_in_group(user, group_name):
    """Return True if the user belongs to the given group name."""
    return user.groups.filter(name=group_name).exists()

def is_coordinator(user):
    return user_in_group(user, 'Coordenador')

def is_auxiliary(user):
    return user_in_group(user, 'Auxiliar Administrativo')
