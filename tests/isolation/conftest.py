import pytest

from tests import support as s


@pytest.fixture
def world(db):
    """Dos empresas con datos equivalentes. Los tests actúan como la Empresa A."""
    a = s.make_tenant('Panaderia A')
    b = s.make_tenant('Panaderia B')
    w = {
        'a': a, 'b': b,
        'admin_a': s.make_user(a, 'admin@a.co', s.ADMIN_ROLE),
        'cashier_a': s.make_user(a, 'cajero@a.co', s.RESTRICTED_ROLE),
        'admin_b': s.make_user(b, 'admin@b.co', s.ADMIN_ROLE),
        'customer_a': s.make_customer(a),
        'customer_b': s.make_customer(b, first_name='Secreto', last_name='DeB'),
        'category_a': s.make_category(a),
        'category_b': s.make_category(b),
        'product_a': s.make_product(a, code='A-001'),
        'product_b': s.make_product(b, code='B-001', price='999000'),
        'supplier_b': s.make_supplier(b),
        'employee_a': s.make_employee(a),
        'employee_b': s.make_employee(b),
    }
    w['invoice_b'] = s.make_invoice(b, w['customer_b'], w['product_b'])
    return w
