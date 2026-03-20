import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')

import django
django.setup()

from django.contrib.auth.models import User

username = 'klismanrds'
u = User.objects.filter(username=username).first()

if u:
    print(f"User: {u.username}")
    print(f"Active: {u.is_active}")
    print(f"Staff: {u.is_staff}")
    print(f"Superuser: {u.is_superuser}")
    print(f"Password set? {u.has_usable_password()}")
else:
    print(f"User {username} not found.")
