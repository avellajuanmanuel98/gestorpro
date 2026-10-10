"""
Prepara el POS en las empresas que ya existían:
- medios de pago por defecto y una "Caja principal" por sucursal activa;
- los permisos nuevos de ventas y caja para los roles de sistema, igual que
  en access/defaults.py (las empresas nuevas los reciben al crearse).
Los roles personalizados no se tocan: los ajusta la empresa.
"""
from django.db import migrations

PERMISSIONS = {
    'sales.sell': 'Vender en el punto de venta (POS)',
    'sales.view': 'Ver sus propias ventas',
    'sales.view_all': 'Ver las ventas de todas las personas',
    'sales.discount': 'Aplicar descuentos en el POS',
    'sales.void': 'Anular ventas (con motivo)',
    'cash.operate': 'Abrir, operar y cerrar su propio turno de caja',
    'cash.manage': 'Ver y cerrar turnos de otras personas y aprobar diferencias grandes de caja',
}
GRANTS = {
    'ADMIN': list(PERMISSIONS),
    'SUPERVISOR': list(PERMISSIONS),
    'CASHIER': ['sales.sell', 'sales.view', 'cash.operate'],
}
METHODS = [('cash', 'Efectivo', 'cash'), ('card', 'Tarjeta', 'card'), ('nequi', 'Nequi', 'wallet'),
           ('daviplata', 'Daviplata', 'wallet'), ('transfer', 'Transferencia', 'transfer')]


def forwards(apps, schema_editor):
    Tenant = apps.get_model('tenancy', 'Tenant')
    Location = apps.get_model('tenancy', 'Location')
    PaymentMethod = apps.get_model('sales', 'PaymentMethod')
    CashRegister = apps.get_model('cash', 'CashRegister')
    Permission = apps.get_model('access', 'Permission')
    Role = apps.get_model('access', 'Role')

    for tenant in Tenant.objects.all():
        for sort, (code, name, kind) in enumerate(METHODS):
            PaymentMethod._base_manager.get_or_create(tenant=tenant, code=code,
                                                      defaults={'name': name, 'kind': kind, 'sort': sort})
        for location in Location._base_manager.filter(tenant=tenant, is_active=True):
            if not CashRegister._base_manager.filter(tenant=tenant, location=location).exists():
                CashRegister._base_manager.create(tenant=tenant, location=location, name='Caja principal')

    perms = {}
    for code, description in PERMISSIONS.items():
        perms[code], _ = Permission.objects.get_or_create(
            code=code, defaults={'module': code.split('.')[0], 'description': description})
    for role_code, codes in GRANTS.items():
        for role in Role._base_manager.filter(code=role_code, is_system=True):
            role.permissions.add(*[perms[c] for c in codes])


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0001_initial'),
        ('cash', '0002_initial'),
        ('access', '0003_invitation'),
        ('tenancy', '0002_alter_location_address_alter_location_is_active_and_more'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
