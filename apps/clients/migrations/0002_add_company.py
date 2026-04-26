# Agrega el campo company a Client en migración separada.
# Así es compatible con despliegues anteriores que ya tenían clients.0001_initial.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='clients',
                to='companies.company',
            ),
        ),
    ]
