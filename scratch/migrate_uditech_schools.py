import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao_qualificacao_profissional.settings')
django.setup()

from escolas.models import Escola

print("=== INICIANDO MIGRACAO DE ESCOLAS UDITECH ===")
uditech_schools = Escola.objects.filter(nome__icontains='uditech')

if not uditech_schools.exists():
    print("Nenhuma escola contendo 'uditech' no nome foi encontrada.")
else:
    for escola in uditech_schools:
        old_tipo = escola.tipo
        if old_tipo != 'UDITECH':
            escola.tipo = 'UDITECH'
            escola.save()
            print(f"[OK] Escola '{escola.nome}' alterada de {old_tipo} to UDITECH.")
        else:
            print(f"[INFO] Escola '{escola.nome}' ja eh do tipo UDITECH.")

print("=== MIGRACAO CONCLUIDA ===")
