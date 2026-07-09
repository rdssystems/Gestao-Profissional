from django.db import migrations
from django.utils.text import slugify


def populate_slugs(apps, schema_editor):
    Escola = apps.get_model('escolas', 'Escola')
    for escola in Escola.objects.filter(slug__isnull=True):
        base = slugify(escola.nome)
        slug = base
        n = 1
        while Escola.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        escola.slug = slug
        escola.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('escolas', '0008_escola_slug'),
    ]

    operations = [
        migrations.RunPython(populate_slugs, reverse_code=migrations.RunPython.noop),
    ]
