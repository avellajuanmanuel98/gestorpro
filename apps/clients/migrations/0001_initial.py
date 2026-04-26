# Migración original — igual a la que Railway ya tiene aplicada.
# Sin campo company (se agrega en 0002_add_company.py).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('CC', 'Cédula de ciudadanía'), ('NIT', 'NIT'), ('CE', 'Cédula de extranjería'), ('PP', 'Pasaporte')], default='CC', max_length=5)),
                ('document_number', models.CharField(max_length=20, unique=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('company_name', models.CharField(blank=True, default='', max_length=200)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(blank=True, default='', max_length=20)),
                ('address', models.TextField(blank=True, default='')),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('status', models.CharField(choices=[('active', 'Activo'), ('inactive', 'Inactivo')], default='active', max_length=10)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='clients_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Cliente',
                'verbose_name_plural': 'Clientes',
                'ordering': ['first_name', 'last_name'],
            },
        ),
    ]
