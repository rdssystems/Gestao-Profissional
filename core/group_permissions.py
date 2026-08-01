"""
Atribuição das permissões dos grupos Coordenador/Auxiliar Administrativo.

Isto ficava em core/migrations/0003_assign_permissions.py como uma
RunPython — mas isso é um erro clássico de ordenação do Django: os
Permission de cada model só são criados pelo sinal post_migrate, que só
dispara depois de TODAS as migrations da mesma chamada de `migrate`
terminarem. Numa base zerada (ex.: `manage.py test`, uma instalação nova),
a migration 0003 rodava ANTES desses Permission existirem e
`Permission.objects.filter(codename__in=[...])` voltava vazio — os grupos
ficavam sem nenhuma permissão, silenciosamente (achado em 2026-08-01: tanto
o banco de dev quanto qualquer banco criado do zero têm os grupos
Coordenador/Auxiliar Administrativo com ZERO permissões).

A correção é conectar isto a post_migrate (que roda depois dos Permission
existirem, toda vez que `migrate` é executado) em vez de deixar numa
migration. Idempotente — pode rodar em todo `migrate` sem problema.
"""
from django.contrib.auth.models import Group, Permission

COORDENADOR_PERMISSIONS = [
    'add_aluno', 'change_aluno', 'delete_aluno', 'view_aluno',
    'add_curso', 'change_curso', 'delete_curso', 'view_curso',
    'add_tipocurso', 'change_tipocurso', 'delete_tipocurso', 'view_tipocurso',
    'add_inscricao', 'change_inscricao', 'delete_inscricao', 'view_inscricao',
    'add_user', 'change_user', 'view_user',
]

AUXILIAR_PERMISSIONS = [
    'change_aluno', 'view_aluno',
    'add_inscricao', 'view_inscricao',
    'view_curso',
    'view_tipocurso',
]


def assign_default_group_permissions(sender=None, **kwargs):
    coordenador_group, _ = Group.objects.get_or_create(name='Coordenador')
    coordenador_group.permissions.set(
        Permission.objects.filter(codename__in=COORDENADOR_PERMISSIONS)
    )

    auxiliar_group, _ = Group.objects.get_or_create(name='Auxiliar Administrativo')
    auxiliar_group.permissions.set(
        Permission.objects.filter(codename__in=AUXILIAR_PERMISSIONS)
    )
