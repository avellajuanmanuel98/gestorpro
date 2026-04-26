"""
Comando para cargar datos de demostración.
Se ejecuta: python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Carga datos de demostración para el portafolio'

    def handle(self, *args, **kwargs):
        self.stdout.write('Cargando datos de demo...')

        # ── Empresa demo ─────────────────────────────
        from apps.companies.models import Company
        company, _ = Company.objects.get_or_create(
            slug='demo-gestorpro',
            defaults={'name': 'Demo GestorPro', 'plan': 'pro'}
        )
        self.stdout.write(self.style.SUCCESS('[OK] Empresa demo creada'))

        # ── Usuario demo ──────────────────────────────
        if not User.objects.filter(email='demo@gestorpro.com').exists():
            User.objects.create_superuser(
                email='demo@gestorpro.com',
                password='demo1234',
                first_name='Demo',
                last_name='GestorPro',
                role='admin',
                company=company,
            )
            self.stdout.write(self.style.SUCCESS('[OK] Usuario demo creado'))
        else:
            # Aseguramos que el usuario demo tenga la empresa asignada
            User.objects.filter(email='demo@gestorpro.com').update(company=company)
            self.stdout.write('  Usuario demo ya existe')

        demo_user = User.objects.get(email='demo@gestorpro.com')

        # ── Clientes ──────────────────────────────────
        from apps.clients.models import Client

        clientes = [
            dict(document_type='NIT', document_number='900123456', first_name='Ferretería',
                 last_name='El Tornillo', company_name='Ferretería El Tornillo SAS',
                 email='contacto@ferreteria.com', phone='3001234567', city='Bogotá', status='active'),
            dict(document_type='CC', document_number='1020304050', first_name='María',
                 last_name='González', company_name='', email='maria@gmail.com',
                 phone='3109876543', city='Medellín', status='active'),
            dict(document_type='NIT', document_number='800987654', first_name='Distribuidora',
                 last_name='Central', company_name='Distribuidora Central Ltda',
                 email='ventas@distribuidora.com', phone='6014567890', city='Bogotá', status='active'),
        ]

        for c in clientes:
            if not Client.objects.filter(email=c['email']).exists():
                Client.objects.create(company=company, created_by=demo_user, **c)

        self.stdout.write(self.style.SUCCESS('[OK] Clientes creados'))

        # ── Categorías y productos ────────────────────
        from apps.inventory.models import Category, Product
        from decimal import Decimal

        cat1, _ = Category.objects.get_or_create(
            name='Ferretería', company=company,
            defaults={'description': 'Herramientas y materiales'}
        )
        cat2, _ = Category.objects.get_or_create(
            name='Servicios', company=company,
            defaults={'description': 'Servicios profesionales'}
        )

        productos = [
            dict(name='Taladro Percutor 700W', code='TAL-001', product_type='product',
                 category=cat1, price=Decimal('185000'), tax_rate=Decimal('19'), stock=15, minimum_stock=3),
            dict(name='Cemento Portland 50kg', code='CEM-001', product_type='product',
                 category=cat1, price=Decimal('32000'), tax_rate=Decimal('0'), stock=80, minimum_stock=20),
            dict(name='Instalación eléctrica', code='SRV-001', product_type='service',
                 category=cat2, price=Decimal('250000'), tax_rate=Decimal('19'), stock=0, minimum_stock=0),
            dict(name='Consultoría técnica (hora)', code='SRV-002', product_type='service',
                 category=cat2, price=Decimal('120000'), tax_rate=Decimal('19'), stock=0, minimum_stock=0),
        ]

        for p in productos:
            if not Product.objects.filter(code=p['code'], company=company).exists():
                Product.objects.create(company=company, created_by=demo_user, **p)

        self.stdout.write(self.style.SUCCESS('[OK] Productos creados'))

        # ── Facturas ──────────────────────────────────
        from apps.billing.models import Invoice, InvoiceItem
        from datetime import date

        cliente1 = Client.objects.get(email='contacto@ferreteria.com')
        cliente2 = Client.objects.get(email='maria@gmail.com')
        taladro  = Product.objects.get(code='TAL-001', company=company)
        cemento  = Product.objects.get(code='CEM-001', company=company)
        servicio = Product.objects.get(code='SRV-001', company=company)

        if not Invoice.objects.filter(number='FAC-2026-001', company=company).exists():
            inv1 = Invoice.objects.create(
                number='FAC-2026-001', invoice_type='invoice', status='paid',
                company=company, client=cliente1, created_by=demo_user,
                issue_date=date(2026, 3, 1), due_date=date(2026, 3, 31),
            )
            InvoiceItem.objects.create(invoice=inv1, product=taladro, quantity=2, unit_price=taladro.price, tax_rate=taladro.tax_rate)
            InvoiceItem.objects.create(invoice=inv1, product=cemento,  quantity=10, unit_price=cemento.price, tax_rate=cemento.tax_rate)

        if not Invoice.objects.filter(number='FAC-2026-002', company=company).exists():
            inv2 = Invoice.objects.create(
                number='FAC-2026-002', invoice_type='invoice', status='sent',
                company=company, client=cliente2, created_by=demo_user,
                issue_date=date(2026, 4, 1), due_date=date(2026, 4, 30),
            )
            InvoiceItem.objects.create(invoice=inv2, product=servicio, quantity=1, unit_price=servicio.price, tax_rate=servicio.tax_rate)

        if not Invoice.objects.filter(number='COT-2026-001', company=company).exists():
            inv3 = Invoice.objects.create(
                number='COT-2026-001', invoice_type='quote', status='draft',
                company=company, client=cliente1, created_by=demo_user,
                issue_date=date(2026, 4, 15), due_date=date(2026, 4, 30),
            )
            InvoiceItem.objects.create(invoice=inv3, product=taladro, quantity=5, unit_price=taladro.price, tax_rate=taladro.tax_rate)
            InvoiceItem.objects.create(invoice=inv3, product=servicio, quantity=2, unit_price=servicio.price, tax_rate=servicio.tax_rate)

        self.stdout.write(self.style.SUCCESS('[OK] Facturas creadas'))
        self.stdout.write(self.style.SUCCESS('\n[LISTO] Datos de demo cargados'))
        self.stdout.write('   Email:    demo@gestorpro.com')
        self.stdout.write('   Password: demo1234')
