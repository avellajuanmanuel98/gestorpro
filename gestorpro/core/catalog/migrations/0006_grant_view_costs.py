"""
Permiso nuevo `catalog.view_costs` para las empresas que ya existían.

Las empresas nuevas lo reciben al crear sus roles de sistema. A las existentes
se les otorga a los roles que ya gestionaban el catálogo (ADMIN, INVENTORY o
roles personalizados con `catalog.manage`) y al SUPERVISOR, igual que en
access/defaults.py. El cajero no ve costos.
"""
from django.db import migrations

CODE = 'catalog.view_costs'


def grant(apps, schema_editor):
    Permission = apps.get_model('access', 'Permission')
    Role = apps.get_model('access', 'Role')
    perm, _ = Permission.objects.get_or_create(
        code=CODE, defaults={'module': 'catalog',
                             'description': 'Ver y registrar costos, márgenes y valor del inventario'})
    roles = Role._base_manager.filter(grants_all=False)
    for role in roles.filter(permissions__code='catalog.manage') | roles.filter(is_system=True, code='SUPERVISOR'):
        role.permissions.add(perm)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_item_cleanup'),
        ('access', '0003_invitation'),
    ]

    operations = [migrations.RunPython(grant, migrations.RunPython.noop)]
