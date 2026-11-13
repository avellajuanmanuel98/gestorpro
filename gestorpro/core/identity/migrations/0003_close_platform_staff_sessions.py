"""
Al exigir verificación en dos pasos al personal de la plataforma, sus sesiones
abiertas (entradas solo con contraseña) se cierran: la próxima vez entran con código.
"""
from django.db import migrations


def close_sessions(apps, schema_editor):
    User = apps.get_model('identity', 'User')
    OutstandingToken = apps.get_model('token_blacklist', 'OutstandingToken')
    BlacklistedToken = apps.get_model('token_blacklist', 'BlacklistedToken')
    staff = User.objects.filter(is_platform_admin=True).values_list('pk', flat=True)
    for token in OutstandingToken.objects.filter(user_id__in=list(staff)):
        BlacklistedToken.objects.get_or_create(token=token)


class Migration(migrations.Migration):
    dependencies = [
        ('identity', '0002_platform_staff_mfa'),
        ('token_blacklist', '0013_alter_blacklistedtoken_options_and_more'),
    ]

    operations = [migrations.RunPython(close_sessions, migrations.RunPython.noop)]
