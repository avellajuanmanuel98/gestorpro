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

from gestorpro.capabilities.production.services import save_recipe
from gestorpro.core.access.services import add_member, provision_tenant
from gestorpro.core.catalog.models import Category, Item, UnitOfMeasure
from gestorpro.core.customers.models import Customer
from gestorpro.core.identity.models import User
from gestorpro.core.inventory import services as inventory
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.core.tenancy.models import Tenant
from gestorpro.verticals.bakery.catalog import load_starter_ingredients

# Productos: (código, nombre, tipo, categoría, unidad, precio COP antes de IVA, IVA %,
#             costo por unidad, existencia, mínimo)
FG, RS = Item.Kind.FINISHED_GOOD, Item.Kind.RESALE
PRODUCTS = [
    ('PAN-001', 'Pan francés', FG, 'Panes', 'und', '1500', '0', '520', '60', '20'),
    ('PAN-002', 'Pan aliñado', FG, 'Panes', 'und', '1200', '0', '430', '50', '20'),
    ('PAN-003', 'Mogolla integral', FG, 'Panes', 'und', '1300', '0', '470', '30', '10'),
    ('PAN-004', 'Pan tajado blanco', FG, 'Panes', 'und', '6500', '0', '2600', '12', '5'),
    ('REL-001', 'Pan de bono', FG, 'Panes rellenos', 'und', '2000', '0', '760', '45', '15'),
    ('REL-002', 'Almojábana', FG, 'Panes rellenos', 'und', '2200', '0', '820', '40', '15'),
    ('REL-003', 'Buñuelo', FG, 'Panes rellenos', 'und', '1800', '0', '650', '8', '15'),
    ('REL-004', 'Roscón de arequipe', FG, 'Panes rellenos', 'und', '3500', '0', '1250', '20', '8'),
    ('REL-005', 'Pan de queso', FG, 'Panes rellenos', 'und', '2500', '0', '900', '25', '10'),
    ('HOJ-001', 'Croissant', FG, 'Hojaldres', 'und', '4200', '0', '1650', '18', '6'),
    ('HOJ-002', 'Pastel de pollo', FG, 'Hojaldres', 'und', '4500', '8', '1900', '14', '6'),
    ('HOJ-003', 'Pastel gloria', FG, 'Hojaldres', 'und', '3200', '0', '1150', '16', '6'),
    ('POS-001', 'Torta negra (porción)', FG, 'Tortas y postres', 'und', '6500', '8', '2400', '10', '4'),
    ('POS-002', 'Torta de naranja (porción)', FG, 'Tortas y postres', 'und', '4800', '8', '1600', '12', '4'),
    ('POS-003', 'Milhoja', FG, 'Tortas y postres', 'und', '5500', '8', '2100', '3', '4'),
    ('GAL-001', 'Galletas de mantequilla (paquete)', FG, 'Galletería', 'und', '5000', '0', '1900', '15', '5'),
    ('BEC-001', 'Tinto', FG, 'Bebidas calientes', 'und', '1800', '8', '0', '0', '0'),
    ('BEC-002', 'Café con leche', FG, 'Bebidas calientes', 'und', '3200', '8', '0', '0', '0'),
    ('BEC-003', 'Chocolate en leche', FG, 'Bebidas calientes', 'und', '4000', '8', '1300', '0', '0'),
    ('BEF-001', 'Jugo natural de mora', FG, 'Bebidas frías', 'und', '5500', '8', '1700', '0', '0'),
    ('REV-001', 'Gaseosa 400 ml', RS, 'Bebidas frías', 'und', '3200', '19', '2100', '36', '12'),
    ('REV-002', 'Agua 600 ml', RS, 'Bebidas frías', 'und', '2500', '19', '1300', '24', '12'),
    ('REV-003', 'Leche entera 1 l', RS, 'Lácteos y otros', 'und', '5200', '0', '4300', '10', '6'),
]

# Bebidas preparadas: al venderse descuentan los ingredientes de su receta
PREPARED_DRINKS = {'BEC-001', 'BEC-002'}

# Recetas demo: (producto, rendimiento, [(ingrediente, cantidad, unidad)])
RECIPES = [
    ('Pan de bono', '40', [('Almidón de yuca', '1000', 'g'), ('Queso costeño', '1000', 'g'), ('Cuajada', '250', 'g'),
                           ('Huevos', '4', 'und'), ('Azúcar blanca', '60', 'g'), ('Leche entera', '100', 'ml')]),
    ('Almojábana', '30', [('Harina de maíz precocida', '500', 'g'), ('Cuajada', '1000', 'g'),
                          ('Queso costeño', '250', 'g'), ('Huevos', '3', 'und'), ('Mantequilla', '100', 'g'),
                          ('Azúcar blanca', '80', 'g'), ('Leche entera', '200', 'ml')]),
    ('Pan francés', '60', [('Harina de trigo', '3', 'kg'), ('Levadura fresca', '90', 'g'), ('Sal', '60', 'g'),
                           ('Azúcar blanca', '60', 'g'), ('Mantequilla', '60', 'g')]),
    ('Tinto', '20', [('Café molido', '100', 'g'), ('Panela', '100', 'g'), ('Vaso desechable 7 oz', '20', 'und')]),
    ('Café con leche', '10', [('Café molido', '60', 'g'), ('Leche entera', '1.5', 'l'), ('Azúcar blanca', '80', 'g'),
                              ('Vaso desechable 7 oz', '10', 'und')]),
]

# Ingredientes: (nombre, costo por unidad COP, existencia, mínimo). Categoría y
# unidad salen del catálogo base del vertical (STARTER_INGREDIENTS).
INGREDIENT_COSTS = {
    'Harina de trigo': ('3200', '85', '50'),
    'Almidón de yuca': ('6800', '18', '10'),
    'Harina de maíz precocida': ('4900', '6', '5'),
    'Leche entera': ('4300', '22', '10'),
    'Huevos': ('560', '180', '120'),
    'Queso costeño': ('24000', '7.5', '5'),
    'Cuajada': ('18000', '3', '4'),
    'Mantequilla': ('32000', '6', '4'),
    'Margarina de hojaldre': ('14500', '12', '5'),
    'Aceite vegetal': ('9800', '15', '6'),
    'Azúcar blanca': ('4200', '40', '20'),
    'Panela': ('5600', '8', '4'),
    'Levadura fresca': ('9500', '2.5', '2'),
    'Sal': ('2100', '10', '3'),
    'Polvo de hornear': ('18000', '1.2', '0.5'),
    'Esencia de vainilla': ('45', '800', '250'),
    'Arequipe': ('15500', '9', '4'),
    'Bocadillo de guayaba': ('11000', '6', '3'),
    'Chocolate de mesa': ('22000', '4', '2'),
    'Café molido': ('38000', '3', '2'),
    'Bolsa de papel pequeña': ('45', '1500', '500'),
    'Bolsa de papel grande': ('95', '600', '300'),
    'Vaso desechable 7 oz': ('120', '400', '200'),
}

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
                                      vertical=Tenant.Vertical.BAKERY, plan_code='pro', city='Bogotá')
            cashier = User.objects.create_user(email='cajero@demo.miga.co', password=password,
                                               first_name='Andrés', last_name='Rojas')
            with tenant_context(tenant):
                add_member(user=cashier, role_code='CASHIER')
                # Las categorías por defecto las crea el vertical al dar de alta la empresa
                categories = {c.name: c for c in Category.objects.filter(kind=Category.Kind.PRODUCT)}
                units = {u.code: u for u in UnitOfMeasure.objects.all()}
                opening = []  # (ítem, existencia): entran al libro de inventario como saldo inicial
                for code, name, kind, category, unit, price, tax, cost, stock, minimum in PRODUCTS:
                    item = Item.objects.create(code=code, name=name, kind=kind, category=categories[category],
                                               unit=units[unit], price=Decimal(price), tax_rate=Decimal(tax),
                                               avg_cost=Decimal(cost), minimum_stock=Decimal(minimum),
                                               consume_on_sale=code in PREPARED_DRINKS)
                    opening.append((item, Decimal(stock)))
                load_starter_ingredients()
                for name, (cost, stock, minimum) in INGREDIENT_COSTS.items():
                    item = Item.objects.get(name=name)
                    item.avg_cost, item.minimum_stock = Decimal(cost), Decimal(minimum)
                    item.save(update_fields=['avg_cost', 'minimum_stock', 'updated_at'])
                    opening.append((item, Decimal(stock)))
                locked = inventory.lock_items([item.id for item, _ in opening])
                location = inventory.default_location()
                for item, stock in opening:
                    if stock > 0 and item.tracks_stock:
                        inventory.post(item=locked[item.id], location=location, type=StockMovement.Type.OPENING,
                                       quantity=stock, unit_cost=locked[item.id].avg_cost, user=owner,
                                       source=inventory.Source('seed', None, 'Datos demo'))
                by_name = {i.name: i for i in Item.objects.select_related('unit')}
                for product, yield_qty, lines in RECIPES:
                    save_recipe(user=owner, product=by_name[product], yield_quantity=yield_qty, lines=[
                        {'ingredient': by_name[ing].id, 'quantity': qty, 'unit': unit} for ing, qty, unit in lines])
                Customer.objects.create(first_name='Café', last_name='El Parque', company_name='Café El Parque SAS',
                                        document_type='NIT', document_number='901234567')
        self.stdout.write(self.style.SUCCESS('Panadería demo creada.'))
        self.stdout.write(f'  Propietaria: propietaria@demo.miga.co / {password}')
        self.stdout.write(f'  Cajero:      cajero@demo.miga.co / {password}')
