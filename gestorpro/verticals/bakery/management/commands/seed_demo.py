"""
Datos de demostración para DESARROLLO.

    python manage.py seed_demo --password "Mi-clave-1"
    (o variable de entorno DEMO_PASSWORD; si no se indica, se genera aleatoria)

- Se niega a ejecutarse con DEBUG=False (nunca corre en producción).
- No crea superusuarios.
- La contraseña viene de --password, de DEMO_PASSWORD o se genera aleatoriamente.
- Es idempotente: si la empresa demo existe, no duplica datos.
"""
import os
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from gestorpro.core.access.services import add_member, provision_tenant
from gestorpro.core.catalog.models import Category, Product
from gestorpro.core.customers.models import Customer
from gestorpro.core.identity.models import User
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant
from gestorpro.verticals.bakery.definition import DEFAULT_CATEGORIES

PRODUCTS = [
    # (código, nombre, categoría, precio COP, IVA %)
    ('PAN-001', 'Pan francés', 'Panes', '1500', '0'),
    ('PAN-002', 'Pan integral', 'Panes', '4500', '0'),
    ('REL-001', 'Buñuelo', 'Panes rellenos', '1800', '8'),
    ('REL-002', 'Pan de bono', 'Panes rellenos', '1800', '8'),
    ('REL-003', 'Empanada de carne', 'Panes rellenos', '3000', '8'),
    ('HOJ-001', 'Croissant', 'Hojaldres', '4500', '8'),
    ('HOJ-002', 'Pan de chocolate', 'Hojaldres', '5000', '8'),
    ('POS-001', 'Torta de zanahoria (porción)', 'Tortas y postres', '7500', '8'),
    ('BEC-001', 'Café tinto', 'Bebidas calientes', '2000', '8'),
    ('BEC-002', 'Capuchino', 'Bebidas calientes', '5500', '8'),
    ('BEC-003', 'Chocolate', 'Bebidas calientes', '4500', '8'),
    ('BEF-001', 'Jugo natural de mora', 'Bebidas frías', '6000', '8'),
]


class Command(BaseCommand):
    help = 'Crea una panadería demo (solo desarrollo).'

    def add_arguments(self, parser):
        parser.add_argument('--password', help='Contraseña de los usuarios demo.')

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('seed_demo solo puede ejecutarse con DEBUG=True.')
        if Tenant.objects.filter(name='Panadería La Espiga (demo)').exists():
            self.stdout.write('La empresa demo ya existe; no se modifica.')
            return
        password = options.get('password') or os.environ.get('DEMO_PASSWORD') or secrets.token_urlsafe(12)
        with transaction.atomic():
            owner = User.objects.create_user(email='propietaria@demo.miga.co', password=password,
                                             first_name='Lucía', last_name='Gómez')
            tenant = provision_tenant(name='Panadería La Espiga (demo)', owner=owner,
                                      vertical=Tenant.Vertical.BAKERY, city='Bogotá')
            cashier = User.objects.create_user(email='cajero@demo.miga.co', password=password,
                                               first_name='Andrés', last_name='Rojas')
            with tenant_context(tenant):
                add_member(user=cashier, role_code='CASHIER')
                categories = {name: Category.objects.create(name=name) for name in DEFAULT_CATEGORIES}
                for code, name, category, price, tax in PRODUCTS:
                    Product.objects.create(code=code, name=name, category=categories[category],
                                           price=Decimal(price), tax_rate=Decimal(tax), stock=40, minimum_stock=10)
                Customer.objects.create(first_name='Consumidor', last_name='final')
                Customer.objects.create(first_name='Café', last_name='El Parque', company_name='Café El Parque SAS',
                                        document_type='NIT', document_number='901234567')
        self.stdout.write(self.style.SUCCESS('Panadería demo creada.'))
        self.stdout.write(f'  Propietaria: propietaria@demo.miga.co / {password}')
        self.stdout.write(f'  Cajero:      cajero@demo.miga.co / {password}')
