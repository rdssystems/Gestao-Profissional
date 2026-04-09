import re
from django.db import migrations

def normalize_existing_data(apps, schema_editor):
    Aluno = apps.get_model('alunos', 'Aluno')
    
    prepositions = ['de', 'da', 'do', 'das', 'dos', 'e']
    
    def normalize_name(name):
        if not name:
            return ""
        words = name.lower().split()
        normalized_words = []
        for i, word in enumerate(words):
            if word in prepositions and i > 0:
                normalized_words.append(word)
            else:
                normalized_words.append(word.capitalize())
        return " ".join(normalized_words)

    def clean_digits(value):
        if not value:
            return ""
        return re.sub(r'\D', '', value)

    for aluno in Aluno.objects.all():
        modified = False
        
        if aluno.nome_completo:
            new_name = normalize_name(aluno.nome_completo)
            if new_name != aluno.nome_completo:
                aluno.nome_completo = new_name
                modified = True
                
        if aluno.cpf:
            new_cpf = clean_digits(aluno.cpf)
            if new_cpf != aluno.cpf:
                # Prevent unique constraint violations (IntegrityError) by checking first
                if Aluno.objects.filter(escola=aluno.escola, cpf=new_cpf).exclude(pk=aluno.pk).exists():
                    new_cpf = f"{new_cpf[:8]}DP{aluno.id}" # Creates a fake unique CPF to avoid crash
                aluno.cpf = new_cpf
                modified = True
        
        # Opcional: Limpar também telefones
        if aluno.whatsapp:
            new_whatsapp = clean_digits(aluno.whatsapp)
            if new_whatsapp != aluno.whatsapp:
                aluno.whatsapp = new_whatsapp
                modified = True
                
        if aluno.telefone_principal:
            new_tel = clean_digits(aluno.telefone_principal)
            if new_tel != aluno.telefone_principal:
                aluno.telefone_principal = new_tel
                modified = True

        if modified:
            aluno.save(update_fields=['nome_completo', 'cpf', 'whatsapp', 'telefone_principal'])

class Migration(migrations.Migration):

    dependencies = [
        ('alunos', '0012_arquivoaluno'),
    ]

    operations = [
        migrations.RunPython(normalize_existing_data),
    ]
