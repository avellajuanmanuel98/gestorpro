"""Fase 7: POS (ventas) y caja."""
import uuid
from decimal import Decimal

import pytest

from gestorpro.core.access.models import Role
from gestorpro.core.audit.models import AuditLog
from gestorpro.core.cash.models import CashMovement, CashRegister
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.sales.models import PaymentMethod, Sale
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db

SALES, SESSIONS = '/api/sales/', '/api/cash/sessions/'


def make_item(tenant, name, price, tax='0', unit='und', stock='20', cost='0', **kw):
    with tenant_context(tenant):
        return Item.objects.create(name=name, code=name[:10].upper(), price=Decimal(price), tax_rate=Decimal(tax),
                                   unit=UnitOfMeasure.objects.get(code=unit), stock=Decimal(stock),
                                   avg_cost=Decimal(cost), **kw)


@pytest.fixture
def pos(db):
    t = s.make_tenant('Panadería POS')
    cashier_user = s.make_user(t, 'caj@pos.co', 'CASHIER')
    with tenant_context(t):
        register = CashRegister.objects.get()
        register2 = CashRegister.objects.create(location=register.location, name='Caja 2')
        methods = {m.code: m.id for m in PaymentMethod.objects.all()}
    ctx = {
        't': t, 'register': register, 'register2': register2, 'methods': methods, 'cashier_user': cashier_user,
        'cashier': s.api_for(cashier_user),
        'supervisor': s.api_for(s.make_user(t, 'sup@pos.co', 'SUPERVISOR')),
        'pan': make_item(t, 'Pan de bono', '2000', cost='760'),
        'gaseosa': make_item(t, 'Gaseosa', '3000', tax='19', stock='10', cost='2100'),
        'queso': make_item(t, 'Queso costeño', '26000', unit='kg', stock='5', cost='20000'),
    }
    return ctx


def open_session(ctx, api='cashier', amount='100000'):
    # El cajero usa la caja principal; el supervisor, la segunda
    register = ctx['register'] if api == 'cashier' else ctx['register2']
    res = ctx[api].post(SESSIONS, {'register': register.id, 'opening_amount': amount}, format='json')
    assert res.status_code == 201, res.content
    return res.data


def sell(ctx, lines, payments, api='cashier', **extra):
    body = {'client_uuid': str(uuid.uuid4()), 'lines': lines, 'payments': payments, **extra}
    return ctx[api].post(SALES, body, format='json')


def cash(ctx, amount):
    return [{'method': ctx['methods']['cash'], 'amount': amount}]


def stock_of(ctx, item):
    with tenant_context(ctx['t']):
        return Item.objects.get(pk=item.pk).stock


# ── Ventas ──────────────────────────────────────────────────────────────────

def test_cannot_sell_without_an_open_cash_session(pos):
    res = sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000'))
    assert res.status_code == 400 and 'turno de caja' in str(res.data)


def test_sale_totals_taxes_and_change_are_computed_by_the_server(pos):
    open_session(pos)
    res = sell(pos, [{'item': pos['pan'].id, 'quantity': '3'}, {'item': pos['gaseosa'].id, 'quantity': '2'}],
               cash(pos, '20000'))
    assert res.status_code == 201, res.content
    # 3 × 2.000 + 2 × 3.000 = 12.000; IVA 19 % de 6.000 = 1.140 → 13.140
    assert res.data['subtotal'] == '12000.00' and res.data['tax_total'] == '1140.00'
    assert res.data['total'] == '13140.00' and res.data['change_given'] == '6860.00'
    assert res.data['number'] == 'V000001' and res.data['customer_name'] == 'Consumidor final'
    payment = res.data['payments'][0]
    assert payment['amount'] == '13140.00' and payment['tendered'] == '20000.00'


def test_client_prices_and_taxes_are_ignored(pos):
    open_session(pos)
    res = sell(pos, [{'item': pos['pan'].id, 'quantity': '1', 'unit_price': '1', 'tax_rate': '0'}],
               cash(pos, '2000'), total='1')
    assert res.status_code == 201 and res.data['total'] == '2000.00'


def test_payments_must_cover_the_total_and_only_cash_gives_change(pos):
    open_session(pos)
    line = [{'item': pos['pan'].id, 'quantity': '2'}]  # 4.000
    short = sell(pos, line, cash(pos, '3000'))
    assert short.status_code == 400 and 'Faltan' in str(short.data)
    card_over = sell(pos, line, [{'method': pos['methods']['card'], 'amount': '5000'}])
    assert card_over.status_code == 400 and 'efectivo' in str(card_over.data)
    mixed = sell(pos, line, [{'method': pos['methods']['nequi'], 'amount': '3000'},
                             {'method': pos['methods']['cash'], 'amount': '2000'}])
    assert mixed.status_code == 201 and mixed.data['change_given'] == '1000.00'
    applied = {p['method_name']: p['amount'] for p in mixed.data['payments']}
    assert applied == {'Nequi': '3000.00', 'Efectivo': '1000.00'}


def test_units_sold_by_piece_require_whole_quantities_but_weight_allows_decimals(pos):
    open_session(pos)
    assert sell(pos, [{'item': pos['pan'].id, 'quantity': '1.5'}], cash(pos, '5000')).status_code == 400
    res = sell(pos, [{'item': pos['queso'].id, 'quantity': '0.25'}], cash(pos, '6500'))
    assert res.status_code == 201 and res.data['total'] == '6500.00'


def test_only_active_sellable_items_can_be_sold(pos):
    open_session(pos)
    flour = make_item(pos['t'], 'Harina', '0', kind='raw_material', is_sellable=False)
    old = make_item(pos['t'], 'Viejo', '1000', is_active=False)
    for item in (flour, old):
        res = sell(pos, [{'item': item.id, 'quantity': '1'}], cash(pos, '1000'))
        assert res.status_code == 400 and 'no está disponible' in str(res.data)


def test_discount_requires_permission_and_cannot_exceed_total(pos):
    open_session(pos)
    line = [{'item': pos['pan'].id, 'quantity': '1'}]
    assert sell(pos, line, cash(pos, '1500'), discount='500').status_code == 403  # cajero sin permiso
    open_session(pos, 'supervisor')
    assert sell(pos, line, cash(pos, '9000'), api='supervisor', discount='5000').status_code == 400
    ok = sell(pos, line, cash(pos, '1500'), api='supervisor', discount='500')
    assert ok.status_code == 201 and ok.data['total'] == '1500.00'


def test_retrying_the_same_sale_does_not_duplicate_it(pos):
    open_session(pos)
    body = {'client_uuid': str(uuid.uuid4()), 'lines': [{'item': pos['pan'].id, 'quantity': '1'}],
            'payments': cash(pos, '2000')}
    first = pos['cashier'].post(SALES, body, format='json')
    again = pos['cashier'].post(SALES, body, format='json')
    assert first.status_code == 201 and again.status_code == 200 and first.data['id'] == again.data['id']
    with tenant_context(pos['t']):
        assert Sale.objects.count() == 1 and CashMovement.objects.filter(type='sale').count() == 1
    assert stock_of(pos, pos['pan']) == Decimal('19')


def test_sale_numbers_are_consecutive(pos):
    open_session(pos)
    numbers = [sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000')).data['number']
               for _ in range(3)]
    assert numbers == ['V000001', 'V000002', 'V000003']


def test_failed_sale_leaves_no_trace_and_does_not_consume_a_number(pos):
    open_session(pos)
    bad = sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], [{'method': 999999, 'amount': '2000'}])
    assert bad.status_code == 400
    ok = sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000'))
    assert ok.data['number'] == 'V000001'
    assert stock_of(pos, pos['pan']) == Decimal('19')


def test_sale_snapshots_cost_and_updates_stock_and_cash(pos):
    session = open_session(pos)
    res = sell(pos, [{'item': pos['pan'].id, 'quantity': '4'}, {'item': pos['gaseosa'].id, 'quantity': '1'}],
               [{'method': pos['methods']['card'], 'amount': '3570'}, {'method': pos['methods']['cash'],
                                                                      'amount': '10000'}])
    assert res.status_code == 201, res.content
    with tenant_context(pos['t']):
        sale = Sale.objects.get()
        assert sale.cost_total == Decimal('4') * 760 + 2100  # costo congelado al vender
        movement = CashMovement.objects.get(type='sale')
        assert movement.amount == Decimal('8000')  # solo el efectivo aplicado entra al cajón
    assert stock_of(pos, pos['pan']) == Decimal('16') and stock_of(pos, pos['gaseosa']) == Decimal('9')
    detail = pos['cashier'].get(f"{SESSIONS}{session['id']}/").data
    assert detail['summary']['expected'] == '108000.00' and detail['summary']['sales_total'] == '11570.00'
    assert {m['method']: m['total'] for m in detail['summary']['by_method']} == {'Efectivo': '8000.00',
                                                                                'Tarjeta': '3570.00'}


def test_stock_may_go_negative_when_production_was_not_registered(pos):
    open_session(pos)
    assert sell(pos, [{'item': pos['gaseosa'].id, 'quantity': '12'}], cash(pos, '50000')).status_code == 201
    assert stock_of(pos, pos['gaseosa']) == Decimal('-2')


# ── Anulación ───────────────────────────────────────────────────────────────

def test_void_requires_permission_reason_and_reverses_cash_and_stock(pos):
    open_session(pos)
    sale = sell(pos, [{'item': pos['pan'].id, 'quantity': '5'}], cash(pos, '10000')).data
    assert pos['cashier'].post(f"{SALES}{sale['id']}/void/", {'reason': 'Error'}, format='json').status_code == 403
    no_reason = pos['supervisor'].post(f"{SALES}{sale['id']}/void/", {'reason': ''}, format='json')
    assert no_reason.status_code == 400
    voided = pos['supervisor'].post(f"{SALES}{sale['id']}/void/", {'reason': 'Cliente se arrepintió'},
                                    format='json')
    assert voided.status_code == 200 and voided.data['status'] == 'voided'
    assert stock_of(pos, pos['pan']) == Decimal('20')
    with tenant_context(pos['t']):
        assert CashMovement.objects.get(type='void').amount == Decimal('-10000')
        assert AuditLog.objects.filter(action='sales.sale.voided').exists()
    again = pos['supervisor'].post(f"{SALES}{sale['id']}/void/", {'reason': 'otra vez'}, format='json')
    assert again.status_code == 400


def test_cannot_void_after_the_cash_session_is_closed(pos):
    session = open_session(pos)
    sale = sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000')).data
    pos['cashier'].post(f"{SESSIONS}{session['id']}/close/", {'counted_amount': '102000'}, format='json')
    res = pos['supervisor'].post(f"{SALES}{sale['id']}/void/", {'reason': 'tarde'}, format='json')
    assert res.status_code == 400 and 'cerró' in str(res.data)


def test_cashier_sees_only_own_sales_supervisor_sees_all(pos):
    open_session(pos)
    sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000'))
    open_session(pos, 'supervisor')
    sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000'), api='supervisor')
    assert pos['cashier'].get(SALES).data['count'] == 1
    assert pos['supervisor'].get(SALES).data['count'] == 2
    other = s.results(pos['supervisor'].get(SALES))
    foreign = next(r for r in other if r['cashier_name'] != s.results(pos['cashier'].get(SALES))[0]['cashier_name'])
    assert pos['cashier'].get(f"{SALES}{foreign['id']}/").status_code == 404


# ── Caja ────────────────────────────────────────────────────────────────────

def test_one_open_session_per_register_and_per_person(pos):
    open_session(pos)
    res = pos['supervisor'].post(SESSIONS, {'register': pos['register'].id, 'opening_amount': '0'}, format='json')
    assert res.status_code == 400 and 'otra persona' in str(res.data)
    res = pos['cashier'].post(SESSIONS, {'register': pos['register2'].id, 'opening_amount': '0'}, format='json')
    assert res.status_code == 400 and 'Ya tienes' in str(res.data)


def test_movements_require_reason_and_cannot_overdraw_the_drawer(pos):
    session = open_session(pos, amount='50000')
    url = f"{SESSIONS}{session['id']}/movements/"
    assert pos['cashier'].post(url, {'type': 'expense', 'amount': '10000', 'reason': ''},
                               format='json').status_code == 400
    assert pos['cashier'].post(url, {'type': 'withdrawal', 'amount': '60000', 'reason': 'Banco'},
                               format='json').status_code == 400
    assert pos['cashier'].post(url, {'type': 'sale', 'amount': '1000', 'reason': 'x'},
                               format='json').status_code == 400  # solo el sistema registra ventas
    for kind, amount in [('income', '20000'), ('expense', '8000'), ('withdrawal', '30000')]:
        assert pos['cashier'].post(url, {'type': kind, 'amount': amount, 'reason': 'motivo'},
                                   format='json').status_code == 201
    summary = pos['cashier'].get(f"{SESSIONS}{session['id']}/").data['summary']
    assert summary['expected'] == '32000.00'  # 50.000 + 20.000 − 8.000 − 30.000
    assert summary['expenses'] == '-8000.00' and summary['withdrawals'] == '-30000.00'


def test_closing_computes_difference_and_requires_explanation(pos):
    session = open_session(pos, amount='50000')
    sell(pos, [{'item': pos['pan'].id, 'quantity': '5'}], cash(pos, '10000'))
    url = f"{SESSIONS}{session['id']}/close/"
    missing = pos['cashier'].post(url, {'counted_amount': '58000'}, format='json')
    assert missing.status_code == 400 and 'note' in missing.data
    closed = pos['cashier'].post(url, {'counted_amount': '58000', 'note': 'Faltó cambio de un billete'},
                                 format='json')
    assert closed.status_code == 200
    assert closed.data['expected_amount'] == '60000.00' and closed.data['difference'] == '-2000.00'
    assert pos['cashier'].get(f"{SESSIONS}current/").data['session'] is None


def test_big_differences_need_a_supervisor(pos):
    session = open_session(pos, amount='50000')
    url = f"{SESSIONS}{session['id']}/close/"
    res = pos['cashier'].post(url, {'counted_amount': '40000', 'note': 'No sé'}, format='json')
    assert res.status_code == 403
    ok = pos['supervisor'].post(url, {'counted_amount': '40000', 'note': 'Revisado con la cajera'}, format='json')
    assert ok.status_code == 200 and ok.data['closed_by_name']


def test_denomination_count_must_match_the_total(pos):
    session = open_session(pos, amount='50000')
    url = f"{SESSIONS}{session['id']}/close/"
    bad = pos['cashier'].post(url, {'counted_amount': '50000', 'denominations': {'20000': 2}}, format='json')
    assert bad.status_code == 400
    ok = pos['cashier'].post(url, {'counted_amount': '50000', 'denominations': {'20000': 2, '10000': 1}},
                             format='json')
    assert ok.status_code == 200 and ok.data['difference'] == '0.00'


def test_cash_movements_are_immutable(pos):
    session = open_session(pos)
    pos['cashier'].post(f"{SESSIONS}{session['id']}/movements/",
                        {'type': 'income', 'amount': '1000', 'reason': 'x'}, format='json')
    with tenant_context(pos['t']):
        movement = CashMovement.objects.get()
        movement.amount = Decimal('999999')
        with pytest.raises(ValueError):
            movement.save()
        with pytest.raises(ValueError):
            movement.delete()


def test_cashier_cannot_operate_someone_elses_session(pos):
    session = open_session(pos, 'supervisor')
    url = f"{SESSIONS}{session['id']}/movements/"
    res = pos['cashier'].post(url, {'type': 'income', 'amount': '1000', 'reason': 'x'}, format='json')
    assert res.status_code == 404  # ni siquiera la ve


def test_today_summary_uses_real_sales(pos):
    open_session(pos)
    sell(pos, [{'item': pos['pan'].id, 'quantity': '2'}], cash(pos, '4000'))
    sell(pos, [{'item': pos['pan'].id, 'quantity': '1'}], cash(pos, '2000'))
    admin = s.api_for(s.make_user(pos['t'], 'adm@pos.co', 'ADMIN'))
    data = admin.get('/api/sales/today/').data
    assert data['count'] == 2 and data['total'] == '6000.00' and data['average_ticket'] == '3000.00'
    assert data['gross_margin'] == '3720.00'  # 6.000 − 3 × 760
    assert pos['cashier'].get('/api/sales/today/').status_code == 403  # el cajero no ve métricas


# ── Configuración inicial ───────────────────────────────────────────────────

def test_new_companies_get_payment_methods_register_and_cashier_permissions(db):
    t = s.make_tenant('Nueva')
    with tenant_context(t):
        assert set(PaymentMethod.objects.values_list('code', flat=True)) == {'cash', 'card', 'nequi', 'daviplata',
                                                                             'transfer'}
        assert CashRegister.objects.get().name == 'Caja principal'
        cashier = set(Role.objects.get(code='CASHIER').permissions.values_list('code', flat=True))
        assert {'sales.sell', 'sales.view', 'cash.operate'} <= cashier
        assert not {'sales.void', 'sales.discount', 'sales.view_all', 'cash.manage'} & cashier


def test_pos_catalog_lists_only_sellable_active_items_with_price_including_tax(pos):
    make_item(pos['t'], 'Harina', '0', kind='raw_material', is_sellable=False)
    data = pos['cashier'].get('/api/sales/catalog/').data
    names = {i['name']: i for i in data['items']}
    assert 'Harina' not in names and names['Gaseosa']['price_with_tax'] == '3570.00'
    assert 'avg_cost' not in names['Gaseosa']  # el POS no expone costos

