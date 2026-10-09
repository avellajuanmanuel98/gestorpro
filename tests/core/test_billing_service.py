"""Facturación: cálculos en servidor, permisos económicos y atomicidad."""
from decimal import Decimal

import pytest

from gestorpro.core.billing.models import Invoice
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    t = s.make_tenant('Facturas')
    customer = s.make_customer(t)
    with tenant_context(t):
        from gestorpro.core.catalog.models import Product
        pan = Product.objects.create(name='Pan', code='P1', price=Decimal('1234.55'), tax_rate=Decimal('19'))
        cafe = Product.objects.create(name='Café', code='C1', price=Decimal('3333.33'), tax_rate=Decimal('5'))
        off = Product.objects.create(name='Viejo', code='V1', price=Decimal('10'), is_active=False)
    return {
        't': t, 'customer': customer, 'pan': pan, 'cafe': cafe, 'off': off,
        'admin': s.api_for(s.make_user(t, 'adm@f.co', 'ADMIN')),
        'cashier': s.api_for(s.make_user(t, 'caj@f.co', 'CASHIER')),
    }


def payload(ctx, items, **extra):
    data = {'number': extra.pop('number', 'F-1'), 'invoice_type': 'invoice', 'customer': ctx['customer'].id,
            'issue_date': '2026-03-01', 'due_date': '2026-03-31', 'items': items}
    data.update(extra)
    return data


def test_totals_are_computed_server_side_with_exact_decimals(ctx):
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, [
        {'product': ctx['pan'].id, 'quantity': '3'},
        {'product': ctx['cafe'].id, 'quantity': '2'},
    ]), format='json')
    assert res.status_code == 201, res.content
    # Pan: 3 × 1234.55 = 3703.65; IVA 19 % = 703.69 (703.6935 → HALF_UP)
    # Café: 2 × 3333.33 = 6666.66; 5 % = 333.33
    assert res.data['subtotal'] == '10370.31'
    assert res.data['tax_amount'] == '1037.02'
    assert res.data['total'] == '11407.33'
    assert res.data['lines'][0]['tax_rate'] == '19.00'


def test_client_cannot_set_tax_rate(ctx):
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, [
        {'product': ctx['pan'].id, 'quantity': '1', 'tax_rate': '0'},
    ]), format='json')
    assert res.status_code == 201
    assert res.data['tax_amount'] == '234.56'


def test_price_override_requires_permission(ctx):
    items = [{'product': ctx['pan'].id, 'quantity': '1', 'unit_price': '500'}]
    assert ctx['cashier'].post(s.ENDPOINTS['invoices'], payload(ctx, items), format='json').status_code == 400
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, items, number='F-2'), format='json')
    assert res.status_code == 201 and res.data['lines'][0]['unit_price'] == '500.00'


def test_discount_requires_permission_and_cannot_exceed_total(ctx):
    items = [{'product': ctx['pan'].id, 'quantity': '1'}]
    assert ctx['cashier'].post(s.ENDPOINTS['invoices'], payload(ctx, items, discount='100'),
                               format='json').status_code == 403
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, items, discount='999999'), format='json')
    assert res.status_code == 400


def test_failed_invoice_leaves_no_partial_data(ctx):
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, [
        {'product': ctx['pan'].id, 'quantity': '1'},
        {'product': ctx['off'].id, 'quantity': '1'},  # inactivo → falla la segunda línea
    ]), format='json')
    assert res.status_code == 400
    with tenant_context(ctx['t']):
        assert not Invoice.objects.exists()


def test_paid_invoice_is_locked_and_cannot_be_deleted(ctx):
    res = ctx['admin'].post(s.ENDPOINTS['invoices'],
                            payload(ctx, [{'product': ctx['pan'].id, 'quantity': '1'}]), format='json')
    url = f"{s.ENDPOINTS['invoices']}{res.data['id']}/"
    assert ctx['admin'].patch(url, {'status': 'paid'}, format='json').status_code == 200
    edit = ctx['admin'].patch(url, {'items': [{'product': ctx['pan'].id, 'quantity': '5'}]}, format='json')
    assert edit.status_code == 400
    assert ctx['admin'].delete(url).status_code == 400


def test_invoice_number_is_unique_per_tenant_with_clear_error(ctx):
    items = [{'product': ctx['pan'].id, 'quantity': '1'}]
    assert ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, items), format='json').status_code == 201
    dup = ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, items), format='json')
    assert dup.status_code == 400


def test_summary_reports_exact_money_strings(ctx):
    ctx['admin'].post(s.ENDPOINTS['invoices'], payload(ctx, [{'product': ctx['pan'].id, 'quantity': '1'}],
                                                      status='paid'), format='json')
    data = ctx['admin'].get(s.ENDPOINTS['billing_summary']).data
    assert data['paid_total'] == '1469.11'


def test_paid_and_cancelled_are_final_states(ctx):
    res = ctx['admin'].post(s.ENDPOINTS['invoices'],
                            payload(ctx, [{'product': ctx['pan'].id, 'quantity': '1'}], number='F-9'), format='json')
    url = f"{s.ENDPOINTS['invoices']}{res.data['id']}/"
    assert ctx['admin'].patch(url, {'status': 'paid'}, format='json').status_code == 200
    for status in ('draft', 'sent', 'cancelled'):
        assert ctx['admin'].patch(url, {'status': status}, format='json').status_code == 400
    res = ctx['admin'].post(s.ENDPOINTS['invoices'],
                            payload(ctx, [{'product': ctx['pan'].id, 'quantity': '1'}], number='F-10'), format='json')
    url = f"{s.ENDPOINTS['invoices']}{res.data['id']}/"
    assert ctx['admin'].patch(url, {'status': 'cancelled'}, format='json').status_code == 200
    assert ctx['admin'].patch(url, {'status': 'paid'}, format='json').status_code == 400
