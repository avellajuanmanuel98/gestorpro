from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('companies', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=200)),
                ('contact_name', models.CharField(blank=True, default='', max_length=200)),
                ('document_type', models.CharField(choices=[('NIT', 'NIT'), ('CC', 'Cédula de ciudadanía'), ('CE', 'Cédula de extranjería'), ('PP', 'Pasaporte')], default='NIT', max_length=5)),
                ('document_number', models.CharField(blank=True, default='', max_length=20)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('phone', models.CharField(blank=True, default='', max_length=20)),
                ('address', models.TextField(blank=True, default='')),
                ('city', models.CharField(blank=True, default='', max_length=100)),
                ('website', models.URLField(blank=True, default='')),
                ('category', models.CharField(choices=[('materials', 'Materiales e insumos'), ('services', 'Servicios'), ('technology', 'Tecnología'), ('logistics', 'Logística y transporte'), ('marketing', 'Marketing y publicidad'), ('other', 'Otro')], default='other', max_length=20)),
                ('status', models.CharField(choices=[('active', 'Activo'), ('inactive', 'Inactivo')], default='active', max_length=10)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='suppliers', to='companies.company')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suppliers_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Proveedor',
                'verbose_name_plural': 'Proveedores',
                'ordering': ['company_name'],
            },
        ),
    ]
