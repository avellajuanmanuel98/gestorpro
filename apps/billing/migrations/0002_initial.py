# Agrega client y company a Invoice.
# null=True para compatibilidad con filas existentes al hacer el deploy.
# La app Django los valida como requeridos a nivel de formulario/serializer.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('billing', '0001_initial'),
        ('clients', '0001_initial'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='client',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invoices',
                to='clients.client',
            ),
        ),
        migrations.AddField(
            model_name='invoice',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='invoices',
                to='companies.company',
            ),
        ),
    ]
