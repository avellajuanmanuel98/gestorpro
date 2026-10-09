"""
Datos de la Fase 6, en su propia migración (PostgreSQL no permite crear índices
en la misma transacción en la que se actualizaron filas con FKs diferidas).
"""
from decimal import Decimal

from django.db import migrations

# (código, nombre, símbolo, dimensión, factor a la base, orden)
UNITS = [
    ('g', 'Gramo', 'g', 'mass', '1', 1),
    ('kg', 'Kilogramo', 'kg', 'mass', '1000', 2),
    ('lb', 'Libra (500 g)', 'lb', 'mass', '500', 3),
    ('arroba', 'Arroba (12,5 kg)', '@', 'mass', '12500', 4),
    ('ml', 'Mililitro', 'ml', 'volume', '1', 1),
    ('l', 'Litro', 'l', 'volume', '1000', 2),
    ('und', 'Unidad', 'und', 'count', '1', 1),
    ('docena', 'Docena', 'doc', 'count', '12', 2),
    ('ciento', 'Ciento', 'cto', 'count', '100', 3),
]


def seed_units(apps, schema_editor):
    UnitOfMeasure = apps.get_model('catalog', 'UnitOfMeasure')
    for code, name, symbol, dimension, factor, sort in UNITS:
        UnitOfMeasure.objects.update_or_create(
            code=code, defaults={'name': name, 'symbol': symbol, 'dimension': dimension,
                                 'factor': Decimal(factor), 'sort': sort},
        )


def fill_items(apps, schema_editor):
    UnitOfMeasure = apps.get_model('catalog', 'UnitOfMeasure')
    Item = apps.get_model('catalog', 'Item')
    und = UnitOfMeasure.objects.get(code='und')
    items = Item._base_manager.all()
    items.update(unit=und, is_sellable=True)
    items.filter(product_type='service').update(kind='service', stock=0, minimum_stock=0)
    items.exclude(product_type='service').update(kind='finished_good')




class Migration(migrations.Migration):

    dependencies = [('catalog', '0004_units_and_item')]

    operations = [
        migrations.RunPython(seed_units, migrations.RunPython.noop),
        migrations.RunPython(fill_items, migrations.RunPython.noop),
    ]
