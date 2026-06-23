from django.db import migrations, models

def set_default_nivel_acesso(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    # Ensure every Profile has a nivel_acesso; default to ADMIN_CP if empty
    Profile.objects.filter(nivel_acesso__isnull=True).update(nivel_acesso='ADMIN_CP')
    # Ensure larissa1937 has a profile with ADMIN_CP
    User = apps.get_model('auth', 'User')
    try:
        user = User.objects.get(username='larissa1937')
    except User.DoesNotExist:
        return
    profile, created = Profile.objects.get_or_create(user=user, defaults={'nivel_acesso': 'ADMIN_CP'})
    if not created:
        profile.nivel_acesso = 'ADMIN_CP'
        profile.save()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_add_email_destinatario'),
    ]
    operations = [
        migrations.RunPython(set_default_nivel_acesso),
    ]
