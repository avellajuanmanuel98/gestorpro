# Migración inicial de billing — contiene el modelo completo.
# Las antiguas 0002 y 0003 fueron colapsadas aquí para evitar
# el error "duplicate column name" que ocurría porque la BD se
# borra en cada deploy y las FK ya estaban en CreateModel.

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('companies', '0001_initial'),
        ('inventory', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=20)),
                ('invoice_type', models.CharField(
                    choices=[('quote', 'Cotización'), ('invoice', 'Factura')],
                    default='invoice',
                    max_length=10,
                )),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Borrador'),
                        ('sent', 'Enviada'),
                        ('paid', 'Pagada'),
                        ('overdue', 'Vencida'),
                        ('cancelled', 'Cancelada'),
                    ],
                    default='draft',
                    max_length=10,
                )),
                ('company', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='invoices',
                    to='companies.company',
                )),
                ('client', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='invoices',
                    to='clients.client',
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='invoices_created',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('issue_date', models.DateField()),
                ('due_date', models.DateField()),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('discount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Factura',
                'verbose_name_plural': 'Facturas',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invoice', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='items',
                    to='billing.invoice',
                )),
                ('product', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='invoice_items',
                    to='inventory.product',
                )),
                ('quantity', models.DecimalField(
                    decimal_places=2,
                    max_digits=10,
                    validators=[django.core.validators.MinValueValidator(Decimal('0.01'))],
                )),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('tax_rate', models.DecimalField(decimal_places=2, default=Decimal('19.00'), max_digits=5)),
                ('description', models.CharField(blank=True, default='', max_length=300)),
            ],
            options={
                'verbose_name': 'Línea de factura',
                'verbose_name_plural': 'Líneas de factura',
            },
        ),
        migrations.AlterUniqueTogether(
            name='invoice',
            unique_together={('company', 'number')},
        ),
    ]
