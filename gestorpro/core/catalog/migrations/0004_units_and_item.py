"""
Fase 6: unidades de medida y paso de `Product` a `Item`.

- Crea y siembra las unidades de medida globales.
- Renombra Product → Item conservando los datos (y las líneas de factura que
  lo referencian).
- Agrega `kind`, `unit`, `is_sellable`, `avg_cost` y `Category.kind`, y los
  rellena (0004b) a partir de `product_type`. La migración 0005 quita `product_type`.
"""
from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0003_alter_category_description_alter_category_name_and_more'),
        ('billing', '0003_alter_invoice_customer_alter_invoice_discount_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitOfMeasure',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=12, unique=True, verbose_name='código')),
                ('name', models.CharField(max_length=40, verbose_name='nombre')),
                ('symbol', models.CharField(max_length=12, verbose_name='símbolo')),
                ('dimension', models.CharField(choices=[('mass', 'Masa'), ('volume', 'Volumen'), ('count', 'Conteo')],
                                               max_length=10, verbose_name='dimensión')),
                ('factor', models.DecimalField(
                    decimal_places=6, max_digits=18, verbose_name='factor a la unidad base',
                    help_text='Unidades base (g, ml, und) que equivalen a 1 de esta unidad.')),
                ('sort', models.PositiveSmallIntegerField(default=0)),
            ],
            options={'verbose_name': 'Unidad de medida', 'verbose_name_plural': 'Unidades de medida',
                     'ordering': ['dimension', 'sort', 'code']},
        ),
        migrations.RenameModel('Product', 'Item'),
        migrations.AddField(
            model_name='item', name='kind',
            field=models.CharField(default='finished_good', max_length=16, verbose_name='tipo', choices=[
                ('finished_good', 'Producto elaborado'), ('resale', 'Reventa'),
                ('raw_material', 'Ingrediente o insumo'), ('service', 'Servicio')]),
        ),
        migrations.AddField(
            model_name='item', name='unit',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+',
                                    to='catalog.unitofmeasure', verbose_name='unidad'),
        ),
        migrations.AddField(
            model_name='item', name='is_sellable',
            field=models.BooleanField(default=True, verbose_name='se vende'),
        ),
        migrations.AddField(
            model_name='item', name='avg_cost',
            field=models.DecimalField(decimal_places=4, default=Decimal('0'), max_digits=14,
                                      verbose_name='costo por unidad'),
        ),
        migrations.AddField(
            model_name='category', name='kind',
            field=models.CharField(choices=[('product', 'Productos'), ('ingredient', 'Ingredientes')],
                                   default='product', max_length=12, verbose_name='tipo'),
        ),
    ]
