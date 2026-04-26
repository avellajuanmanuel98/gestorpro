# Agrega el campo company al modelo User.
# Va en una migración separada para no romper el historial
# de despliegues anteriores que ya tenían users.0001_initial aplicado.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='company',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='members',
                to='companies.company',
            ),
        ),
    ]
