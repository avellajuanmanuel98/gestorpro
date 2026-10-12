"""
Enciende el módulo 'production' en las empresas que ya lo usan: las panaderías y
cualquier empresa que ya tenga registros. Las demás lo encienden en Configuración → Empresa.
"""
from django.db import migrations

MODULE = 'production'
MODELS = ['Recipe', 'ProductionBatch']


def enable(apps, schema_editor):
    Tenant = apps.get_model('tenancy', 'Tenant')
    used = set()
    for model in MODELS:
        used.update(apps.get_model('production', model).objects.values_list('tenant_id', flat=True).distinct())
    for tenant in Tenant.objects.all():
        if (tenant.vertical == 'bakery' or tenant.id in used) and MODULE not in (tenant.modules or []):
            tenant.modules = sorted([*(tenant.modules or []), MODULE])
            tenant.save(update_fields=['modules'])


class Migration(migrations.Migration):
    dependencies = [
        ('production', '0001_initial'),
        ('tenancy', '0003_tenant_modules'),
    ]

    operations = [migrations.RunPython(enable, migrations.RunPython.noop)]
