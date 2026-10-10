"""
Prepara las empresas existentes para la Fase 8:
- motivos de merma por defecto;
- permisos nuevos (inventario, compras, recetas, producción, mermas) para los
  roles de sistema, igual que en access/defaults.py.
"""
from django.db import migrations

PERMISSIONS = {
    'inventory.view': ('inventory', 'Ver existencias por sucursal y movimientos de inventario (kardex)'),
    'inventory.adjust': ('inventory', 'Registrar conteos físicos y ajustes de inventario'),
    'purchases.view': ('purchasing', 'Ver compras (recepción de mercancía)'),
    'purchases.create': ('purchasing', 'Registrar compras: suben las existencias y actualizan el costo promedio'),
    'recipes.view': ('production', 'Ver recetas'),
    'recipes.manage': ('production', 'Crear y modificar recetas'),
    'production.view': ('production', 'Ver los lotes de producción'),
    'production.register': ('production', 'Registrar producción: consume ingredientes y suma producto terminado'),
    'waste.view': ('waste', 'Ver mermas registradas'),
    'waste.register': ('waste', 'Registrar mermas (producto o ingrediente perdido)'),
}
ALL = list(PERMISSIONS)
GRANTS = {
    'ADMIN': ALL,
    'INVENTORY': ALL,
    'SUPERVISOR': ['inventory.view', 'purchases.view', 'recipes.view', 'production.view', 'production.register',
                   'waste.view', 'waste.register'],
    'CASHIER': ['waste.register'],
}
REASONS = [('unsold', 'Sobrante del día'), ('burnt', 'Quemado o mal horneado'), ('expired', 'Vencido'),
           ('damaged', 'Dañado o caído'), ('tasting', 'Degustación'), ('staff', 'Consumo del personal')]


def forwards(apps, schema_editor):
    Tenant = apps.get_model('tenancy', 'Tenant')
    WasteReason = apps.get_model('waste', 'WasteReason')
    Permission = apps.get_model('access', 'Permission')
    Role = apps.get_model('access', 'Role')

    for tenant in Tenant.objects.all():
        for sort, (code, name) in enumerate(REASONS):
            WasteReason._base_manager.get_or_create(tenant=tenant, code=code, defaults={'name': name, 'sort': sort})

    perms = {}
    for code, (module, description) in PERMISSIONS.items():
        perms[code], _ = Permission.objects.get_or_create(code=code, defaults={'module': module,
                                                                               'description': description})
    for role_code, codes in GRANTS.items():
        for role in Role._base_manager.filter(code=role_code, is_system=True):
            role.permissions.add(*[perms[c] for c in codes])


class Migration(migrations.Migration):

    dependencies = [
        ('waste', '0001_initial'),
        ('access', '0003_invitation'),
        ('tenancy', '0002_alter_location_address_alter_location_is_active_and_more'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
