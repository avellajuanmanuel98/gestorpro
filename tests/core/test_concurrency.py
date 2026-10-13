"""
Fase 11: concurrencia REAL contra PostgreSQL.

Cada test lanza varios hilos con su propia conexión y transacción, liberados a
la vez con una barrera, contra los servicios de dominio. Lo que se verifica no
es "que no falle", sino que el resultado sea el mismo que si las operaciones
hubieran ocurrido una detrás de otra: existencias exactas, consecutivos sin
huecos ni repetidos, costo promedio coherente con el libro, un solo turno por
caja, una sola anulación, límites del plan respetados.
"""
import threading
import uuid
from decimal import Decimal

import pytest
from django.db import connection

from gestorpro.core.access import services as access
from gestorpro.core.access.models import Membership, Role
from gestorpro.core.cash import services as cash
from gestorpro.core.cash.models import CashMovement, CashRegister, CashSession
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.inventory.models import StockLevel, StockMovement
from gestorpro.core.purchasing.services import register_purchase
from gestorpro.core.sales import services as sales
from gestorpro.core.sales.models import PaymentMethod, Sale
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

# serialized_rollback: el vaciado entre tests no se lleva los datos de las migraciones (planes, unidades…)
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def run_together(tenant, *calls):
    """
    Ejecuta cada `call` en su propio hilo, todos liberados a la vez. Devuelve,
    en el mismo orden, el resultado o la excepción de cada uno.
    """
    barrier = threading.Barrier(len(calls))
    out = [None] * len(calls)

    def worker(i, fn):
        try:
            with tenant_context(tenant):
                barrier.wait(timeout=10)
                out[i] = fn()
        except Exception as exc:  # noqa: BLE001 — el test decide qué esperaba
            out[i] = exc
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, fn)) for i, fn in enumerate(calls)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), 'un hilo quedó bloqueado (¿interbloqueo?)'
    return out


def errors(results):
    return [r for r in results if isinstance(r, Exception)]


@pytest.fixture
def shop():
    t = s.make_tenant('Panadería Concurrente')
    users = [s.make_user(t, f'caj{i}@conc.co', 'CASHIER') for i in range(3)]
    supervisor = s.make_user(t, 'sup@conc.co', 'SUPERVISOR')
    with tenant_context(t):
        first = CashRegister.objects.get()
        registers = [first] + [CashRegister.objects.create(location=first.location, name=f'Caja {i}')
                               for i in (2, 3)]
        unit = UnitOfMeasure.objects.get(code='und')
        pan = Item.objects.create(name='Pan', code='PAN', price=Decimal('1000'), tax_rate=Decimal('0'),
                                  unit=unit, avg_cost=Decimal('400'))
        harina = Item.objects.create(name='Harina', code='HAR', kind=Item.Kind.RAW_MATERIAL, price=Decimal('0'),
                                     unit=unit, is_sellable=False)
        methods = {m.code: m for m in PaymentMethod.objects.all()}
        members = {u.email: Membership.objects.get(user=u) for u in [*users, supervisor]}
    return {'t': t, 'users': users, 'supervisor': supervisor, 'registers': registers, 'pan': pan,
            'harina': harina, 'methods': methods, 'members': members}


def member(shop, user):
    return shop['members'][user.email]


def open_for(shop, i, amount='50000'):
    with tenant_context(shop['t']):
        return cash.open_session(user=shop['users'][i], register=shop['registers'][i], opening_amount=amount)


def sale_call(shop, user, qty='1', client_uuid=None):
    paid = str(int(qty) * 1000)

    def call():
        return sales.complete_sale(membership=member(shop, user), client_uuid=client_uuid or uuid.uuid4(),
                                   lines=[{'item': shop['pan'].id, 'quantity': qty}],
                                   payments=[{'method': shop['methods']['cash'].id, 'amount': paid}])
    return call


def assert_ledger_consistent(shop, item):
    """El libro manda: existencia, existencia por sucursal y último saldo deben coincidir."""
    with tenant_context(shop['t']):
        item = Item.objects.get(pk=item.pk)
        moves = list(StockMovement.objects.filter(item=item).order_by('id'))
        ledger = sum((m.quantity for m in moves), Decimal('0'))
        by_location = sum((lv.quantity for lv in StockLevel.objects.filter(item=item)), Decimal('0'))
        assert item.stock == ledger == by_location
        if moves:
            assert moves[-1].balance_after == item.stock
            assert moves[-1].avg_cost_after == item.avg_cost
        return item


# ── Ventas ──────────────────────────────────────────────────────────────────

def test_parallel_sales_from_three_registers_keep_stock_numbers_and_cash_exact(shop):
    for i in range(3):
        open_for(shop, i)
    calls = [sale_call(shop, shop['users'][i % 3]) for i in range(12)]
    results = run_together(shop['t'], *calls)
    assert errors(results) == []

    with tenant_context(shop['t']):
        numbers = sorted(Sale.objects.values_list('number', flat=True))
        assert numbers == [f'V{n:06d}' for n in range(1, 13)]  # sin huecos ni repetidos
        for session in CashSession.objects.all():
            sold = Sale.objects.filter(cash_session=session).count()
            assert sold == 4
            assert cash.expected_amount(session) == Decimal('50000') + 4 * Decimal('1000')
    pan = assert_ledger_consistent(shop, shop['pan'])
    assert pan.stock == Decimal('-12')  # se permite negativo en panadería


def test_the_same_sale_sent_twice_at_once_is_registered_once(shop):
    """Un reintento de la tablet (misma client_uuid) no duplica la venta ni la rechaza."""
    open_for(shop, 0)
    same = uuid.uuid4()
    results = run_together(shop['t'], sale_call(shop, shop['users'][0], client_uuid=same),
                           sale_call(shop, shop['users'][0], client_uuid=same))
    assert errors(results) == []
    (a, created_a), (b, created_b) = results
    assert a.pk == b.pk and sorted([created_a, created_b]) == [False, True]
    with tenant_context(shop['t']):
        assert Sale.objects.count() == 1
        assert CashMovement.objects.filter(type=CashMovement.Type.SALE).count() == 1
    assert assert_ledger_consistent(shop, shop['pan']).stock == Decimal('-1')


def test_a_sale_racing_the_cash_close_is_either_counted_or_rejected(shop):
    """Nunca queda una venta dentro de un turno ya cerrado sin estar en su esperado."""
    session = open_for(shop, 0)
    sup = member(shop, shop['supervisor'])

    def close():
        return cash.close_session(membership=sup, session=session, counted_amount='50000', note='cierre de prueba')

    for _ in range(5):  # varias rondas: el orden de llegada cambia
        with tenant_context(shop['t']):
            session = CashSession.objects.filter(status=CashSession.Status.OPEN).first() or open_for(shop, 0)
        results = run_together(shop['t'], sale_call(shop, shop['users'][0]), close)
        sale_result, close_result = results
        assert not isinstance(close_result, Exception), close_result
        with tenant_context(shop['t']):
            closed = CashSession.objects.get(pk=session.pk)
            in_session = Sale.objects.filter(cash_session=closed).count()
            assert closed.expected_amount == Decimal('50000') + in_session * Decimal('1000')
            assert closed.expected_amount == closed.opening_amount + cash.movements_total(closed)
        if isinstance(sale_result, Exception):
            assert 'cerrad' in str(sale_result) or 'Abre tu turno' in str(sale_result)
        else:
            assert sale_result[0].cash_session_id == session.pk


def test_voiding_the_same_sale_twice_at_once_reverts_it_once(shop):
    open_for(shop, 0)
    with tenant_context(shop['t']):
        sale, _ = sale_call(shop, shop['users'][0], qty='3')()
    sup = member(shop, shop['supervisor'])

    def void():
        return sales.void_sale(membership=sup, sale=sale, reason='Cliente desistió')

    results = run_together(shop['t'], void, void)
    assert len(errors(results)) == 1 and 'ya está anulada' in str(errors(results)[0])
    with tenant_context(shop['t']):
        assert CashMovement.objects.filter(type=CashMovement.Type.VOID).count() == 1
        assert StockMovement.objects.filter(type=StockMovement.Type.SALE_VOID).count() == 1
    assert assert_ledger_consistent(shop, shop['pan']).stock == Decimal('0')


# ── Caja ────────────────────────────────────────────────────────────────────

def test_two_people_opening_the_same_register_at_once_get_one_session(shop):
    register = shop['registers'][0]

    def opener(user):
        return lambda: cash.open_session(user=user, register=register, opening_amount='10000')

    results = run_together(shop['t'], opener(shop['users'][0]), opener(shop['users'][1]))
    assert len(errors(results)) == 1
    with tenant_context(shop['t']):
        assert CashSession.objects.filter(register=register, status=CashSession.Status.OPEN).count() == 1


def test_parallel_cash_withdrawals_cannot_leave_the_drawer_negative(shop):
    session = open_for(shop, 0, amount='30000')
    sup = member(shop, shop['supervisor'])

    def withdraw():
        return cash.add_movement(membership=sup, session=session, type=CashMovement.Type.WITHDRAWAL,
                                 amount='20000', reason='Consignación')

    results = run_together(shop['t'], withdraw, withdraw)
    assert len(errors(results)) == 1
    with tenant_context(shop['t']):
        assert cash.expected_amount(CashSession.objects.get(pk=session.pk)) == Decimal('10000')


# ── Inventario ──────────────────────────────────────────────────────────────

def test_parallel_purchases_produce_the_same_average_cost_as_in_sequence(shop):
    """Costo promedio ponderado: el resultado se puede recalcular desde el libro, en su orden."""
    sup = shop['supervisor']
    costs = ['1000', '1200', '1500', '900', '1100', '1300']

    def buy(cost):
        return lambda: register_purchase(user=sup, received_on='2026-10-01',
                                         lines=[{'item': shop['harina'].id, 'quantity': '10', 'unit_cost': cost}])

    results = run_together(shop['t'], *[buy(c) for c in costs])
    assert errors(results) == []
    harina = assert_ledger_consistent(shop, shop['harina'])
    assert harina.stock == Decimal('60')

    with tenant_context(shop['t']):
        stock, avg = Decimal('0'), Decimal('0')
        for move in StockMovement.objects.filter(item=harina).order_by('id'):
            avg = move.unit_cost if stock <= 0 else ((stock * avg + move.quantity * move.unit_cost)
                                                     / (stock + move.quantity)).quantize(Decimal('0.0001'))
            stock += move.quantity
            assert move.avg_cost_after == avg
        receipts = sorted(r.number for r in results)
    assert harina.avg_cost == avg == Decimal('1166.6667')  # promedio simple: todas son de 10 unidades
    assert receipts == [f'C{n:06d}' for n in range(1, 7)]


def test_selling_while_receiving_a_purchase_keeps_the_ledger_consistent(shop):
    open_for(shop, 0)
    sup = shop['supervisor']
    with tenant_context(shop['t']):
        Item.objects.filter(pk=shop['pan'].pk).update(avg_cost=Decimal('0'))

    def buy():
        return register_purchase(user=sup, received_on='2026-10-01',
                                 lines=[{'item': shop['pan'].id, 'quantity': '20', 'unit_cost': '450'}])

    calls = [buy] + [sale_call(shop, shop['users'][0]) for _ in range(5)]
    assert errors(run_together(shop['t'], *calls)) == []
    pan = assert_ledger_consistent(shop, shop['pan'])
    assert pan.stock == Decimal('15')
    with tenant_context(shop['t']):
        # Cada venta salió al promedio vigente en su momento: 0 antes de la compra, 450 después
        for move in StockMovement.objects.filter(item=pan, type=StockMovement.Type.SALE):
            assert move.unit_cost in (Decimal('0'), Decimal('450'))


# ── Límites del plan ────────────────────────────────────────────────────────

def test_parallel_invitations_cannot_exceed_the_plan_seats():
    """Plan Starter: 3 usuarios. Con 2 ocupados, dos invitaciones simultáneas → solo entra una."""
    t = s.make_tenant('Starter Concurrente', plan_code='starter')
    s.make_user(t, 'segundo@starter.co', 'CASHIER')
    with tenant_context(t):
        owner = Membership.objects.get(role__code='OWNER')
        cashier_role = Role.objects.get(code='CASHIER')
        assert access.seats_in_use() == 2

    def inviting(email):
        return lambda: access.invite(actor=owner, email=email, role=cashier_role)

    results = run_together(t, inviting('a@starter.co'), inviting('b@starter.co'))
    assert len(errors(results)) == 1 and 'plan' in str(errors(results)[0]).lower()
    with tenant_context(t):
        assert access.seats_in_use() == 3


def test_a_physical_count_racing_sales_leaves_the_counted_quantity_or_later_sales(shop):
    """El conteo se aplica sobre la existencia del momento: lo vendido después se descuenta del contado."""
    open_for(shop, 0)
    sup = shop['supervisor']
    with tenant_context(shop['t']):
        location = CashRegister.objects.get(pk=shop['registers'][0].pk).location

    def count():
        from gestorpro.core.inventory.services import physical_count
        return physical_count(user=sup, location=location, counts=[{'item': shop['pan'].id, 'counted': '50'}])

    calls = [count] + [sale_call(shop, shop['users'][0]) for _ in range(4)]
    assert errors(run_together(shop['t'], *calls)) == []
    pan = assert_ledger_consistent(shop, shop['pan'])
    with tenant_context(shop['t']):
        count_move = StockMovement.objects.get(item=pan, source_type='count')
        sold_after = StockMovement.objects.filter(item=pan, type=StockMovement.Type.SALE, id__gt=count_move.id).count()
    assert count_move.balance_after == Decimal('50')
    assert pan.stock == Decimal('50') - sold_after
