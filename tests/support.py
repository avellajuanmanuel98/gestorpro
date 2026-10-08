"""
Capa de adaptación entre los tests y el modelo de dominio.

Los tests de aislamiento describen *comportamientos* (qué no debe poder hacer
un usuario de la Empresa A sobre datos de la Empresa B) y no cambian cuando
cambia la arquitectura. Lo único que cambia es CÓMO se crean los datos de
prueba y DÓNDE viven los endpoints: eso vive aquí.

Versión: MULTI-TENANT (Tenant + Membership + roles por empresa).
La versión LEGACY de este archivo está en el commit 9a1012b.
"""
import datetime
from decimal import Decimal

from rest_framework.test import APIClient

from gestorpro.core.tenancy.context import tenant_context

PASSWORD = 'Test-pass-1234!'

ENDPOINTS = {
    'customers': '/api/customers/',
    'products': '/api/catalog/products/',
    'categories': '/api/catalog/categories/',
    'invoices': '/api/billing/invoices/',
    'suppliers': '/api/suppliers/',
    'employees': '/api/employees/',
    'login': '/api/auth/login/',
    'billing_summary': '/api/billing/summary/',
    'report_billing': '/api/reports/billing/',
    'report_inventory': '/api/reports/inventory/',
}

RESTRICTED_ROLE = 'CASHIER'
ADMIN_ROLE = 'ADMIN'


def _user(email, **extra):
    from gestorpro.core.identity.models import User
    return User.objects.create_user(email=email, password=PASSWORD, first_name='Test', last_name=email, **extra)


def make_tenant(name):
    from gestorpro.core.access.services import provision_tenant
    owner = _user(f"owner@{name.lower().replace(' ', '-')}.co")
    return provision_tenant(name=name, owner=owner)


def make_user(tenant, email, role=ADMIN_ROLE):
    from gestorpro.core.access.services import add_member
    user = _user(email)
    with tenant_context(tenant):
        add_member(user=user, role_code=role)
    return user


def make_user_without_tenant(email):
    return _user(email)


def make_customer(tenant, **kw):
    from gestorpro.core.customers.models import Customer
    data = dict(first_name='Cliente', last_name=tenant.name, email=f'c@{tenant.slug}.co',
                document_number=f'DOC-{tenant.slug}')
    data.update(kw)
    with tenant_context(tenant):
        return Customer.objects.create(**data)


def make_category(tenant, name='Panes'):
    from gestorpro.core.catalog.models import Category
    with tenant_context(tenant):
        return Category.objects.create(name=name)


def make_product(tenant, code='PAN-001', price='1000', **kw):
    from gestorpro.core.catalog.models import Product
    with tenant_context(tenant):
        return Product.objects.create(name=f'Producto {tenant.name}', code=code, price=Decimal(price),
                                      tax_rate=Decimal('0'), stock=10, **kw)


def make_supplier(tenant):
    from gestorpro.core.suppliers.models import Supplier
    with tenant_context(tenant):
        return Supplier.objects.create(company_name=f'Proveedor {tenant.name}')


def make_employee(tenant):
    from gestorpro.capabilities.hr.models import Employee
    with tenant_context(tenant):
        return Employee.objects.create(document_number='1', first_name='E', last_name='E', email='e@e.co',
                                       position='Panadero', hire_date=datetime.date(2026, 1, 1),
                                       salary=Decimal('1800000'))


def make_invoice(tenant, customer, product):
    from gestorpro.core.billing.models import Invoice, InvoiceLine
    today = datetime.date.today()
    with tenant_context(tenant):
        inv = Invoice.objects.create(customer=customer, number=f'F-{Invoice.all_tenants.count() + 1}',
                                     status='paid', issue_date=today, due_date=today,
                                     subtotal=product.price, total=product.price)
        InvoiceLine.objects.create(invoice=inv, product=product, quantity=1, unit_price=product.price,
                                   tax_rate=Decimal('0'), line_subtotal=product.price, tax_amount=Decimal('0'),
                                   line_total=product.price)
        return inv


def scoped_query_without_context():
    """Ejecuta una consulta de un modelo de negocio SIN contexto de tenant."""
    from gestorpro.core.customers.models import Customer
    return list(Customer.objects.all())


def api_for(user):
    """Cliente autenticado por el flujo real de login (JWT), no force_authenticate."""
    client = APIClient()
    res = client.post(ENDPOINTS['login'], {'email': user.email, 'password': PASSWORD}, format='json')
    assert res.status_code == 200, res.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return client


def invoice_payload(customer_id, product_id, unit_price='1000', number='F-100'):
    return {
        'number': number, 'invoice_type': 'invoice', 'customer': customer_id,
        'issue_date': '2026-01-01', 'due_date': '2026-01-31',
        'items': [{'product': product_id, 'quantity': '1', 'unit_price': unit_price}],
    }


def results(res):
    data = res.data
    return data['results'] if isinstance(data, dict) and 'results' in data else data
