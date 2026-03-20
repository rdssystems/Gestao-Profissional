import os
import sys
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
import django
django.setup()
from django.contrib.auth.models import User
for u in User.objects.all():
    print(f"User: {u.username}, Active: {u.is_active}, Staff: {u.is_staff}, Groups: {[g.name for g in u.groups.all()]}")
