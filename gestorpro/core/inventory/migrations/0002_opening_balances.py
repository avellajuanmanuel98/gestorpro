"""
Pasa las existencias que había al libro de inventario.

Antes de la Fase 8, `Item.stock` era un número editable. Aquí cada existencia
distinta de cero se convierte en un movimiento de "Saldo inicial" en la
sucursal principal, al costo que tenía el ítem. Desde ahora, el libro y
`Item.stock` cuadran siempre. Las ventas anteriores ya habían descontado su
existencia, así que no generan movimientos adicionales.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Item = apps.get_model('catalog', 'Item')
    Location = apps.get_model('tenancy', 'Location')
    StockLevel = apps.get_model('inventory', 'StockLevel')
    StockMovement = apps.get_model('inventory', 'StockMovement')

    for item in Item._base_manager.exclude(stock=0).exclude(kind='service').exclude(consume_on_sale=True):
        location = (Location._base_manager.filter(tenant_id=item.tenant_id, is_default=True).first()
                    or Location._base_manager.filter(tenant_id=item.tenant_id).order_by('id').first())
        if location is None:
            continue
        StockLevel._base_manager.create(tenant_id=item.tenant_id, item=item, location=location, quantity=item.stock)
        # Un saldo negativo (ventas antes de registrar producción) entra como ajuste de faltante
        kind = 'opening' if item.stock > 0 else 'adjustment_out'
        StockMovement._base_manager.create(
            tenant_id=item.tenant_id, item=item, location=location, type=kind, quantity=item.stock,
            unit_cost=item.avg_cost, total_cost=item.stock * item.avg_cost, balance_after=item.stock,
            avg_cost_after=item.avg_cost, source_type='migration', source_label='Saldo al iniciar el inventario',
            reason='Existencia registrada antes del libro de inventario')


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('catalog', '0007_item_consume_on_sale'),
    ]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
