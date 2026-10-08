# Fase 0 (contención): la cuenta demo con credenciales públicas era superusuario.
# Se le retiran los privilegios y se invalida su contraseña en cualquier BD existente.
from django.db import migrations


def revoke(apps, schema_editor):
    User = apps.get_model('users', 'User')
    for user in User.objects.filter(email='demo@gestorpro.com'):
        user.is_superuser = False
        user.is_staff = False
        user.password = '!'  # contraseña inutilizable (formato de make_password(None))
        user.save(update_fields=['is_superuser', 'is_staff', 'password'])


class Migration(migrations.Migration):
    dependencies = [('users', '0002_add_company_fk')]
    operations = [migrations.RunPython(revoke, migrations.RunPython.noop)]
