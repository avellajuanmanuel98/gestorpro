"""
Fase 11: invariantes contables bajo una simulación de un día de operación.

Una secuencia pseudoaleatoria (con semilla fija, así que es reproducible) de
ventas con varios medios de pago y descuentos, anulaciones, compras,
producciones, mermas, conteos físicos y movimientos y cierres de caja. Las
operaciones que el negocio debe rechazar (pagar de menos, anular dos veces…)
se intentan también y deben fallar sin dejar rastro.

Al final, TODO debe cuadrar, sin importar el orden en que pasaron las cosas:

  Inventario   existencia = Σ libro = Σ existencias por sucursal; el costo
               promedio se puede recalcular repitiendo el libro.
  Ventas       total = subtotal + IVA − descuento = Σ pagos; cada línea cuadra.
  Ventas ↔ inventario
               cada venta descuenta exactamente sus líneas (o la receta de
               las bebidas preparadas); una anulada queda en cero neto.
  Caja         esperado = base + Σ movimientos; el efectivo de las ventas es
               el que entró al cajón; lo anulado salió.
  Analítica    las cifras del tablero salen de las mismas ventas: ni una más.
"""
import random
import uuid
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import pytest
from rest_framework.exceptions import APIException

from gestorpro.capabilities.production.services import produce, save_recipe
from gestorpro.capabilities.waste.models import WasteReason
from gestorpro.capabilities.waste.services import register_waste
from gestorpro.core.access.models import Membership
from gestorpro.core.analytics import periods
from gestorpro.core.analytics.services import sales_totals
from gestorpro.core.cash import services as cash
from gestorpro.core.cash.models import CashMovement, CashRegister, CashSession
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.inventory.models import StockLevel, StockMovement
from gestorpro.core.inventory.services import default_location, physical_count
from gestorpro.core.purchasing.services import register_purchase
from gestorpro.core.sales import services as sales
from gestorpro.core.sales.models import Payment, PaymentMethod, Sale
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.kernel.money import money
from tests import support as s

pytestmark = pytest.mark.django_db

Q4 = Decimal('0.0001')


def _item(name, kind, unit, price='0', tax='0', **kw):
    return Item.objects.create(name=name, code=name[:12].upper(), kind=kind, price=Decimal(price),
                               tax_rate=Decimal(tax), unit=UnitOfMeasure.objects.get(code=unit), **kw)


class Day:
    """Un día simulado de una panadería con dos cajas."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.t = s.make_tenant(f'Simulación {seed}')
        cashier = s.make_user(self.t, f'caja{seed}@sim.co', 'CASHIER')
        with tenant_context(self.t):
            self.owner = Membership.objects.get(role__code='OWNER')
            self.cashier = Membership.objects.get(user=cashier)
            first = CashRegister.objects.get()
            self.registers = {self.owner.user_id: first,
                              cashier.id: CashRegister.objects.create(location=first.location, name='Caja 2')}
            self.methods = list(PaymentMethod.objects.all())
            self.cash_method = next(m for m in self.methods if m.affects_cash_drawer)
            F, R, RAW = Item.Kind.FINISHED_GOOD, Item.Kind.RESALE, Item.Kind.RAW_MATERIAL
            self.harina = _item('Harina', RAW, 'kg', is_sellable=False)
            self.mantequilla = _item('Mantequilla', RAW, 'kg', is_sellable=False)
            self.cafe = _item('Café molido', RAW, 'g', is_sellable=False)
            self.pan = _item('Pan de bono', F, 'und', '2000')
            self.croissant = _item('Croissant', F, 'und', '4500', tax='8')
            self.gaseosa = _item('Gaseosa', R, 'und', '3000', tax='19')
            self.queso = _item('Queso', R, 'kg', '26000', tax='5')
            self.tinto = _item('Tinto', F, 'und', '1500', consume_on_sale=True)
            user = self.owner.user
            self.recipes = {
                self.pan.id: save_recipe(user=user, product=self.pan, yield_quantity='40', lines=[
                    {'ingredient': self.harina.id, 'quantity': '2'},
                    {'ingredient': self.mantequilla.id, 'quantity': '300', 'unit': 'g'}]),
                self.croissant.id: save_recipe(user=user, product=self.croissant, yield_quantity='12', lines=[
                    {'ingredient': self.harina.id, 'quantity': '1'},
                    {'ingredient': self.mantequilla.id, 'quantity': '0.5', 'waste_pct': '5'}]),
            }
            save_recipe(user=user, product=self.tinto, yield_quantity='1',
                        lines=[{'ingredient': self.cafe.id, 'quantity': '10'}])
            self.reason = WasteReason.objects.first()
            self.location = default_location()
        self.sellable = [self.pan, self.croissant, self.gaseosa, self.queso, self.tinto]
        self.stockable = [self.harina, self.mantequilla, self.cafe, self.pan, self.croissant, self.gaseosa,
                          self.queso]
        self.rejected = 0

    # ── operaciones ─────────────────────────────────────────────────────────
    def who(self):
        return self.rng.choice([self.owner, self.cashier])

    def ensure_open(self, m):
        if cash.current_session(m.user) is None:
            cash.open_session(user=m.user, register=self.registers[m.user_id],
                              opening_amount=self.rng.choice(['50000', '100000', '0']))

    def qty(self, item):
        if item.unit.code == 'kg':
            return str(Decimal(self.rng.randint(1, 1500)) / 1000)
        return str(self.rng.randint(1, 6))

    def sale(self):
        m = self.who()
        self.ensure_open(m)
        lines = [{'item': self.rng.choice(self.sellable).id, 'quantity': None}
                 for _ in range(self.rng.randint(1, 4))]
        for line in lines:
            line['quantity'] = self.qty(Item.objects.get(pk=line['item']))
        # El total se calcula aquí solo para pagar; el servidor lo recalcula y es el que vale
        gross = sum((money(Decimal(ln['quantity']) * it.price) + money(money(Decimal(ln['quantity']) * it.price)
                     * it.tax_rate / 100) for ln in lines for it in [Item.objects.get(pk=ln['item'])]),
                    Decimal('0'))
        discount = None
        if m is self.owner and self.rng.random() < 0.2:
            discount = str(money(gross * Decimal(self.rng.choice(['0.05', '0.1']))))
        total = gross - Decimal(discount or 0)
        style = self.rng.random()
        if style < 0.5:    # efectivo, a veces con billete grande
            payments = [{'method': self.cash_method.id, 'amount': str(total + self.rng.choice([0, 0, 500, 10000]))}]
        elif style < 0.8:  # otro medio por el total exacto
            other = self.rng.choice([x for x in self.methods if not x.affects_cash_drawer])
            payments = [{'method': other.id, 'amount': str(total)}]
        else:              # mixto
            part = money(total / 2)
            other = self.rng.choice([x for x in self.methods if not x.affects_cash_drawer])
            payments = [{'method': other.id, 'amount': str(part)},
                        {'method': self.cash_method.id, 'amount': str(total - part + 1000)}]
        if self.rng.random() < 0.05:  # paga de menos: debe rechazarse
            payments = [{'method': self.cash_method.id, 'amount': str(total - 1)}]
        sales.complete_sale(membership=m, client_uuid=uuid.uuid4(), lines=lines, payments=payments,
                            discount=discount)

    def void(self):
        open_sessions = CashSession.objects.filter(status=CashSession.Status.OPEN)
        candidates = list(Sale.objects.filter(cash_session__in=open_sessions))
        if not candidates:
            return
        # A veces se elige una ya anulada: debe rechazarse
        sales.void_sale(membership=self.owner, sale=self.rng.choice(candidates), reason='Error de digitación')

    def purchase(self):
        item = self.rng.choice([self.harina, self.mantequilla, self.cafe, self.gaseosa, self.queso])
        unit_costs = {'kg': (1800, 26000), 'g': (20, 60), 'und': (1500, 2200)}
        low, high = unit_costs[item.unit.code]
        qty = {'kg': str(self.rng.randint(5, 50)), 'g': str(self.rng.randint(500, 3000)),
               'und': str(self.rng.randint(12, 48))}[item.unit.code]
        register_purchase(user=self.owner.user, received_on='2026-10-12',
                          lines=[{'item': item.id, 'quantity': qty, 'unit_cost': str(self.rng.randint(low, high))}])

    def production(self):
        product_id = self.rng.choice(list(self.recipes))
        recipe = self.recipes[product_id]
        produce(user=self.owner.user, recipe=recipe, quantity=str(int(recipe.yield_quantity)
                                                                    * self.rng.randint(1, 3)))

    def waste(self):
        item = self.rng.choice(self.stockable)
        register_waste(user=self.owner.user, item_id=item.id, quantity=self.qty(item) if item.unit.code != 'g'
                       else '50', reason=self.reason)

    def count(self):
        item = self.rng.choice(self.stockable)
        counted = max(Decimal('0'), Item.objects.get(pk=item.pk).stock + self.rng.randint(-3, 3))
        physical_count(user=self.owner.user, location=self.location,
                       counts=[{'item': item.id, 'counted': str(counted)}])

    def cash_movement(self):
        session = CashSession.objects.filter(status=CashSession.Status.OPEN).first()
        if session is None:
            return
        kind = self.rng.choice([CashMovement.Type.INCOME, CashMovement.Type.EXPENSE, CashMovement.Type.WITHDRAWAL])
        cash.add_movement(membership=self.owner, session=session, type=kind,
                          amount=str(self.rng.choice([2000, 15000, 80000, 500000])), reason='Simulación')

    def close(self):
        session = CashSession.objects.filter(status=CashSession.Status.OPEN).first()
        if session is None:
            return
        expected = cash.expected_amount(session)
        counted = expected + self.rng.choice([0, 0, 0, -1000, 2000])
        cash.close_session(membership=self.owner, session=session, counted_amount=str(counted),
                           note='' if counted == expected else 'Diferencia en el conteo')

    def run(self, steps):
        ops = [(self.sale, 45), (self.void, 6), (self.purchase, 10), (self.production, 8), (self.waste, 6),
               (self.count, 5), (self.cash_movement, 8), (self.close, 4)]
        fns, weights = zip(*ops, strict=True)
        with tenant_context(self.t):
            for _ in range(steps):
                op = self.rng.choices(fns, weights)[0]
                try:
                    op()
                except APIException:
                    self.rejected += 1  # rechazo legítimo del negocio: no debe dejar rastro


@pytest.mark.parametrize('seed', [7, 2026, 31337])
def test_after_a_simulated_day_everything_reconciles(seed):
    day = Day(seed)
    day.run(steps=220)
    with tenant_context(day.t):
        assert Sale.objects.count() > 40, 'la simulación debe vender lo suficiente para ser significativa'
        assert day.rejected > 0, 'la simulación debe intentar también operaciones inválidas'
        check_inventory(day)
        check_sales(day)
        check_sales_vs_inventory(day)
        check_cash()
        check_analytics(day)


# ── verificaciones ──────────────────────────────────────────────────────────

def check_inventory(day):
    for item in Item.objects.all():
        moves = list(StockMovement.objects.filter(item=item).order_by('id'))
        if not item.tracks_stock:
            assert moves == [] and item.stock == 0, item.name
            continue
        levels = sum((lv.quantity for lv in StockLevel.objects.filter(item=item)), Decimal('0'))
        assert item.stock == sum((m.quantity for m in moves), Decimal('0')) == levels, item.name
        stock, avg = Decimal('0'), Decimal('0')
        for move in moves:  # repetir el libro reproduce el costo promedio guardado
            # Entradas con costo propio (el sobrante de un conteo entra al promedio vigente)
            costed_entry = move.type in (StockMovement.Type.PURCHASE, StockMovement.Type.PRODUCTION_OUTPUT,
                                         StockMovement.Type.OPENING, StockMovement.Type.SALE_VOID)
            if costed_entry:
                if stock <= 0:
                    avg = move.unit_cost
                else:
                    weighted = (stock * avg + move.quantity * move.unit_cost) / (stock + move.quantity)
                    avg = weighted.quantize(Q4, ROUND_HALF_UP)
            stock += move.quantity
            assert move.balance_after == stock and move.avg_cost_after == avg, (item.name, move.id)
            assert move.total_cost == (move.quantity * move.unit_cost).quantize(Q4, ROUND_HALF_UP)
        assert item.avg_cost == avg, item.name


def check_sales(day):
    for sale in Sale.objects.prefetch_related('lines', 'payments__method'):
        lines = list(sale.lines.all())
        for line in lines:
            assert line.line_subtotal == money(line.quantity * line.unit_price)
            assert line.line_total == line.line_subtotal + line.tax_amount
        assert sale.subtotal == sum(ln.line_subtotal for ln in lines)
        assert sale.tax_total == sum(ln.tax_amount for ln in lines)
        assert sale.total == sale.subtotal + sale.tax_total - sale.discount >= 0
        assert sum(p.amount for p in sale.payments.all()) == sale.total
        assert sale.change_given >= 0
        # El precio es siempre el del catálogo (el POS no envía precios)
        for line in lines:
            assert line.unit_price == line.item.price


def check_sales_vs_inventory(day):
    for sale in Sale.objects.prefetch_related('lines__item'):
        expected = defaultdict(lambda: Decimal('0'))
        for line in sale.lines.all():
            if line.item.consume_on_sale:
                expected[day.cafe.id] -= line.quantity * 10
            elif line.item.tracks_stock:
                expected[line.item_id] -= line.quantity
        actual = defaultdict(lambda: Decimal('0'))
        for move in StockMovement.objects.filter(source_type='sale', source_id=sale.id):
            actual[move.item_id] += move.quantity
        if sale.status == Sale.Status.VOIDED:
            assert all(v == 0 for v in actual.values()), sale.number
        else:
            assert {k: v for k, v in actual.items() if v} == {k: v for k, v in expected.items() if v}, sale.number


def check_cash():
    for session in CashSession.objects.all():
        moves = session.movements.all()
        sales_cash = Payment.objects.filter(sale__cash_session=session, method__kind=PaymentMethod.Kind.CASH)
        cash_in = sum((p.amount for p in sales_cash), Decimal('0'))
        voided_cash = sum((p.amount for p in sales_cash.filter(sale__status=Sale.Status.VOIDED)), Decimal('0'))
        assert sum((m.amount for m in moves.filter(type=CashMovement.Type.SALE)), Decimal('0')) == cash_in
        assert sum((m.amount for m in moves.filter(type=CashMovement.Type.VOID)), Decimal('0')) == -voided_cash
        if session.status == CashSession.Status.CLOSED:
            assert session.expected_amount == session.opening_amount + cash.movements_total(session)
            assert session.difference == session.counted_amount - session.expected_amount
            assert not Sale.objects.filter(cash_session=session, created_at__gt=session.closed_at).exists()
        assert cash.expected_amount(session) >= 0


def check_analytics(day):
    today = periods.resolve(day.t, 'today').current
    totals = sales_totals(today)
    completed = Sale.objects.filter(status=Sale.Status.COMPLETED)
    assert totals['transactions'] == completed.count()
    assert totals['sales'] == sum(x.total for x in completed)
    assert totals['net_revenue'] == sum(x.total - x.tax_total for x in completed)
    assert totals['cost_of_sales'] == money(sum(x.cost_total for x in completed))
    waste = StockMovement.objects.filter(type=StockMovement.Type.WASTE)
    assert totals['waste_cost'] == money(-sum((m.total_cost for m in waste), Decimal('0')))
