# Agrega company a Category y Product en migración separada.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('companies', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='categories',
                to='companies.company',
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='company',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='products',
                to='companies.company',
            ),
        ),
    ]
