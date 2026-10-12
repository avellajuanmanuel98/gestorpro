"""
"Quemado o mal horneado" es un motivo de panadería: se desactiva en las demás
empresas si nunca lo usaron (si lo usaron, se deja: es su historia).
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Tenant = apps.get_model('tenancy', 'Tenant')
    WasteReason = apps.get_model('waste', 'WasteReason')
    WasteRecord = apps.get_model('waste', 'WasteRecord')
    generic = Tenant.objects.exclude(vertical='bakery').values_list('id', flat=True)
    used = WasteRecord.objects.values_list('reason_id', flat=True)
    WasteReason.objects.filter(tenant_id__in=generic, code='burnt').exclude(id__in=used).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('waste', '0003_enable_module')]
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
