"""
Capa de adaptación entre los tests y el modelo de dominio.

Los tests de aislamiento describen *comportamientos* (qué no debe poder hacer
un usuario de la Empresa A sobre datos de la Empresa B) y no deben cambiar
cuando cambie la arquitectura. Lo único que cambia entre la versión legacy y la
nueva es CÓMO se crean los datos de prueba y DÓNDE viven los endpoints: eso
vive aquí.

Versión: LEGACY (apps.companies / apps.users con FK company + role).
"""
from decimal import Decimal

from rest_framework.test import APIClient

PASSWORD = 'Test-pass-1234!'

ENDPOINTS = {
    'customers': '/api/clients/',
    'products': '/api/inventory/products/',
    'categories': '/api/inventory/categories/',
    'invoices': '/api/billing/invoices/',
    'suppliers': '/api/suppliers/',
    'employees': '/api/employees/',
    'login': '/api/auth/login/',
    'billing_summary': '/api/billing/summary/',
    'report_billing': '/api/reports/billing/',
    'report_inventory': '/api/reports/inventory/',
}

# Rol "operativo" sin privilegios administrativos (cajero).
RESTRICTED_ROLE = 'employee'
ADMIN_ROLE = 'admin'


def make_tenant(name):
    from apps.companies.models import Company
    return Company.objects.create(name=name, slug=name.lower().replace(' ', '-'))


def make_user(tenant, email, role=ADMIN_ROLE):
    from apps.users.models import User
    return User.objects.create_user(
        email=email, password=PASSWORD, first_name='Test', last_name=email,
        company=tenant, role=role,
    )


def make_user_without_tenant(email):
    from apps.users.models import User
    return User.objects.create_user(email=email, password=PASSWORD, first_name='Sin', last_name='Empresa')


def make_customer(tenant, **kw):
    from apps.clients.models import Client
    data = dict(first_name='Cliente', last_name=tenant.name, email=f'c@{tenant.slug}.co',
                document_number=f'DOC-{tenant.slug}')
    data.update(kw)
    return Client.objects.create(company=tenant, **data)


def make_category(tenant, name='Panes'):
    from apps.inventory.models import Category
    return Category.objects.create(company=tenant, name=name)


def make_product(tenant, code='PAN-001', price='1000', **kw):
    from apps.inventory.models import Product
    return Product.objects.create(company=tenant, name=f'Producto {tenant.name}', code=code,
                                  price=Decimal(price), stock=10, **kw)


def make_supplier(tenant):
    from apps.suppliers.models import Supplier
    return Supplier.objects.create(company=tenant, company_name=f'Proveedor {tenant.name}')


def make_employee(tenant):
    import datetime
    from apps.employees.models import Employee
    return Employee.objects.create(company=tenant, document_number='1', first_name='E', last_name='E',
                                   email='e@e.co', position='Panadero', hire_date=datetime.date(2026, 1, 1),
                                   salary=Decimal('1800000'))


def make_invoice(tenant, customer, product):
    import datetime
    from apps.billing.models import Invoice, InvoiceItem
    inv = Invoice.objects.create(company=tenant, client=customer, number='F-1', status='paid',
                                 issue_date=datetime.date.today(), due_date=datetime.date.today())
    InvoiceItem.objects.create(invoice=inv, product=product, quantity=1,
                               unit_price=product.price, tax_rate=Decimal('0'))
    return inv


def scoped_query_without_context():
    """Ejecuta una consulta de un modelo de negocio SIN contexto de tenant."""
    from apps.clients.models import Client
    return list(Client.objects.all())


def api_for(user):
    """Cliente autenticado por el flujo real de login (JWT), no force_authenticate."""
    client = APIClient()
    res = client.post(ENDPOINTS['login'], {'email': user.email, 'password': PASSWORD}, format='json')
    assert res.status_code == 200, res.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


def invoice_payload(customer_id, product_id, unit_price='1000', number='F-100'):
    return {
        'number': number, 'invoice_type': 'invoice', 'client': customer_id,
        'issue_date': '2026-01-01', 'due_date': '2026-01-31',
        'items': [{'product': product_id, 'quantity': '1', 'unit_price': unit_price, 'tax_rate': '0'}],
    }


def results(res):
    data = res.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data
