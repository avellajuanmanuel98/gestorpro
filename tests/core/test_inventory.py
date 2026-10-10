"""Fase 8: libro de inventario, costo promedio ponderado, compras, recetas, producción, mermas y conteos."""
import uuid
from decimal import Decimal

import pytest

from gestorpro.core.access.models import Role
from gestorpro.core.cash.models import CashRegister
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.inventory.models import StockLevel, StockMovement
from gestorpro.core.sales.models import PaymentMethod
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

pytestmark = pytest.mark.django_db

ITEMS, PURCHASES, RECIPES, BATCHES = '/api/catalog/items/', '/api/purchases/', '/api/production/recipes/', \
    '/api/production/batches/'


@pytest.fixture
def inv(db):
    t = s.make_tenant('Inventario')
    admin = s.api_for(s.make_user(t, 'adm@inv.co', 'ADMIN'))

    def create(**data):
        res = admin.post(ITEMS, data, format='json')
        assert res.status_code == 201, res.content
        return res.data['id']

    ids = {
        'harina': create(name='Harina', kind='raw_material', unit='kg'),
        'almidon': create(name='Almidón de yuca', kind='raw_material', unit='kg', avg_cost='6800', stock='10'),
        'queso': create(name='Queso costeño', kind='raw_material', unit='kg', avg_cost='24000', stock='10'),
        'huevos': create(name='Huevos', kind='raw_material', unit='und', avg_cost='560', stock='100'),
        'leche': create(name='Leche', kind='raw_material', unit='l', avg_cost='4300', stock='20'),
        'pan': create(name='Pan de bono', kind='finished_good', price='2000'),
        'cafe': create(name='Café molido', kind='raw_material', unit='kg', avg_cost='38000', stock='2'),
        'vaso': create(name='Vaso', kind='raw_material', unit='und', avg_cost='120', stock='100'),
    }
    return {'t': t, 'admin': admin, **ids}


def item(ctx, key):
    with tenant_context(ctx['t']):
        return Item.objects.get(pk=ctx[key])


def buy(ctx, lines, **extra):
    body = {'received_on': '2026-10-10', 'lines': lines, **extra}
    return ctx['admin'].post(PURCHASES, body, format='json')


# ── Costo promedio ponderado ────────────────────────────────────────────────

def test_purchases_update_stock_and_weighted_average_cost(inv):
    assert buy(inv, [{'item': inv['harina'], 'quantity': '10', 'unit_cost': '3000'}]).status_code == 201
    assert item(inv, 'harina').avg_cost == Decimal('3000')
    buy(inv, [{'item': inv['harina'], 'quantity': '10', 'unit_cost': '4000'}])
    h = item(inv, 'harina')
    assert h.stock == Decimal('20') and h.avg_cost == Decimal('3500')  # (10×3000 + 10×4000) / 20
    kardex = inv['admin'].get('/api/inventory/movements/', {'item': inv['harina']}).data['results']
    assert [(m['type'], m['balance_after'], m['avg_cost_after']) for m in reversed(kardex)] == [
        ('purchase', '10.0000', '3000.0000'), ('purchase', '20.0000', '3500.0000')]


def test_purchase_converts_purchase_units_and_computes_totals(inv):
    res = buy(inv, [{'item': inv['harina'], 'quantity': '2', 'unit': 'arroba', 'unit_cost': '40000'}])
    assert res.status_code == 201, res.content
    line = res.data['lines'][0]
    assert res.data['total'] == '80000.00' and res.data['number'] == 'C000001'
    assert line['base_quantity'] == '25.0000' and line['base_unit_cost'] == '3200.0000'  # 2 @ = 25 kg
    bad = buy(inv, [{'item': inv['harina'], 'quantity': '1', 'unit': 'l', 'unit_cost': '1000'}])
    assert bad.status_code == 400 and 'no se puede comprar' in str(bad.data)


def test_outbound_movements_freeze_the_cost_of_their_moment(inv):
    buy(inv, [{'item': inv['harina'], 'quantity': '10', 'unit_cost': '3000'}])
    inv['admin'].post('/api/inventory/counts/', {'counts': [{'item': inv['harina'], 'counted': '8'}]}, format='json')
    buy(inv, [{'item': inv['harina'], 'quantity': '8', 'unit_cost': '5000'}])  # nuevo promedio 4000
    with tenant_context(inv['t']):
        shortage = StockMovement.objects.get(type='adjustment_out')
    assert shortage.unit_cost == Decimal('3000') and shortage.total_cost == Decimal('-6000')
    assert item(inv, 'harina').avg_cost == Decimal('4000')


def test_after_negative_stock_the_next_purchase_sets_the_cost(inv):
    inv['admin'].post('/api/inventory/counts/', {'counts': [{'item': inv['huevos'], 'counted': '0'}]}, format='json')
    with tenant_context(inv['t']):
        Item.objects.filter(pk=inv['huevos']).update(stock=-12)  # vendido antes de registrar la compra
    buy(inv, [{'item': inv['huevos'], 'quantity': '30', 'unit_cost': '600'}])
    h = item(inv, 'huevos')
    assert h.stock == Decimal('18') and h.avg_cost == Decimal('600')


def test_stock_and_cost_are_not_edited_by_hand(inv):
    url = f"{ITEMS}{inv['queso']}/"
    assert inv['admin'].patch(url, {'stock': '50'}, format='json').status_code == 400
    assert inv['admin'].patch(url, {'avg_cost': '1'}, format='json').status_code == 400  # tiene existencias
    assert inv['admin'].patch(f"{ITEMS}{inv['harina']}/", {'avg_cost': '3100'}, format='json').status_code == 200
    with tenant_context(inv['t']):
        opening = StockMovement.objects.get(item_id=inv['queso'])
        assert opening.type == 'opening' and opening.quantity == Decimal('10')
        assert StockLevel.objects.get(item_id=inv['queso']).quantity == Decimal('10')


def test_movements_are_immutable(inv):
    with tenant_context(inv['t']):
        movement = StockMovement.objects.filter(item_id=inv['queso']).first()
        movement.quantity = Decimal('999')
        with pytest.raises(ValueError):
            movement.save()
        with pytest.raises(ValueError):
            movement.delete()


# ── Conteo físico ───────────────────────────────────────────────────────────

def test_physical_count_records_surplus_and_shortage(inv):
    res = inv['admin'].post('/api/inventory/counts/', {'note': 'Conteo del lunes', 'counts': [
        {'item': inv['almidon'], 'counted': '12'}, {'item': inv['queso'], 'counted': '9.5'},
        {'item': inv['huevos'], 'counted': '100'}]}, format='json')
    assert res.status_code == 201, res.content
    types = sorted((a['item_name'], a['type'], a['quantity']) for a in res.data['adjustments'])
    assert types == [('Almidón de yuca', 'adjustment_in', '2.0000'), ('Queso costeño', 'adjustment_out', '-0.5000')]
    cashier = s.api_for(s.make_user(inv['t'], 'caj@inv.co', 'CASHIER'))
    assert cashier.post('/api/inventory/counts/', {'counts': [{'item': inv['queso'], 'counted': '1'}]},
                        format='json').status_code == 403


def test_kardex_hides_costs_without_cost_permission(inv):
    with tenant_context(inv['t']):
        Role.objects.get(code='SUPERVISOR').permissions.remove('catalog.view_costs')
    supervisor = s.api_for(s.make_user(inv['t'], 'sup@inv.co', 'SUPERVISOR'))
    row = supervisor.get('/api/inventory/movements/').data['results'][0]
    assert 'quantity' in row and not {'unit_cost', 'total_cost', 'avg_cost_after'} & row.keys()


# ── Recetas y producción ────────────────────────────────────────────────────

def pan_de_bono_recipe(inv, yield_qty='40'):
    return inv['admin'].post(RECIPES, {'product': inv['pan'], 'yield_quantity': yield_qty, 'lines': [
        {'ingredient': inv['almidon'], 'quantity': '1000', 'unit': 'g'},
        {'ingredient': inv['queso'], 'quantity': '1', 'unit': 'kg', 'waste_pct': '10'},
        {'ingredient': inv['huevos'], 'quantity': '4', 'unit': 'und'},
        {'ingredient': inv['leche'], 'quantity': '100', 'unit': 'ml'},
    ]}, format='json')


def test_recipe_cost_converts_units_and_applies_waste(inv):
    res = pan_de_bono_recipe(inv)
    assert res.status_code == 201, res.content
    # 1 kg × 6.800 + 1,1 kg × 24.000 + 4 × 560 + 0,1 l × 4.300 = 35.870 → /40 = 896,75
    assert res.data['cost']['total'] == '35870.0000' and res.data['cost']['unit_cost'] == '896.7500'
    assert res.data['cost']['margin_pct'] == '55.2'
    queso = next(line for line in res.data['lines'] if line['ingredient_name'] == 'Queso costeño')
    assert queso['base_quantity'] == '1.1000'


def test_recipe_validation(inv):
    def post(lines, product=None):
        return inv['admin'].post(RECIPES, {'product': product or inv['pan'], 'yield_quantity': '10',
                                           'lines': lines}, format='json')
    assert post([{'ingredient': inv['leche'], 'quantity': '1', 'unit': 'kg'}]).status_code == 400  # l ≠ kg
    assert post([{'ingredient': inv['pan'], 'quantity': '1'}]).status_code == 400  # a sí mismo
    assert post([{'ingredient': inv['huevos'], 'quantity': '1'}], product=inv['harina']).status_code == 400
    assert post([{'ingredient': inv['huevos'], 'quantity': '1'}, {'ingredient': inv['huevos'], 'quantity': '2'}]
                ).status_code == 400  # repetido


def test_production_consumes_ingredients_and_values_the_product(inv):
    recipe = pan_de_bono_recipe(inv).data
    plan = inv['admin'].get(f"{RECIPES}{recipe['id']}/plan/", {'quantity': '80'}).data
    assert {line['name']: line['quantity'] for line in plan['lines']}['Huevos'] == '8.0000'
    res = inv['admin'].post(BATCHES, {'recipe': recipe['id'], 'quantity': '80',
                                      'actual': {str(inv['huevos']): '9'}}, format='json')
    assert res.status_code == 201, res.content
    # 2 × (6.800 + 26.400 + 430) + 9 × 560 = 72.300 → /80 = 903,75
    assert res.data['total_cost'] == '72300.0000' and res.data['unit_cost'] == '903.7500'
    assert res.data['number'] == 'P000001'
    assert item(inv, 'pan').stock == Decimal('80') and item(inv, 'pan').avg_cost == Decimal('903.75')
    assert item(inv, 'almidon').stock == Decimal('8') and item(inv, 'huevos').stock == Decimal('91')
    assert inv['admin'].post(BATCHES, {'recipe': recipe['id'], 'quantity': '10',
                                       'actual': {str(inv['harina']): '1'}}, format='json').status_code == 400


def test_changing_a_used_recipe_creates_a_new_version(inv):
    v1 = pan_de_bono_recipe(inv).data
    same = pan_de_bono_recipe(inv, yield_qty='45').data  # sin producción: se edita en el lugar
    assert same['id'] == v1['id'] and same['version'] == 1
    batch = inv['admin'].post(BATCHES, {'recipe': v1['id'], 'quantity': '45'}, format='json').data
    v2 = pan_de_bono_recipe(inv, yield_qty='50').data
    assert v2['version'] == 2 and v2['id'] != v1['id']
    assert inv['admin'].get(RECIPES).data['count'] == 1  # solo la activa
    assert batch['recipe_version'] == 1
    stale = inv['admin'].post(BATCHES, {'recipe': v1['id'], 'quantity': '10'}, format='json')
    assert stale.status_code == 400


# ── Ventas con inventario ───────────────────────────────────────────────────

@pytest.fixture
def pos(inv):
    t = inv['t']
    with tenant_context(t):
        register = CashRegister.objects.get()
        cash = PaymentMethod.objects.get(code='cash')
    cashier = s.api_for(s.make_user(t, 'caj2@inv.co', 'CASHIER'))
    cashier.post('/api/cash/sessions/', {'register': register.id, 'opening_amount': '0'}, format='json')
    return {**inv, 'cashier': cashier, 'cash': cash.id}


def sell(ctx, item_id, qty, amount):
    return ctx['cashier'].post('/api/sales/', {'client_uuid': str(uuid.uuid4()),
                                               'lines': [{'item': item_id, 'quantity': qty}],
                                               'payments': [{'method': ctx['cash'], 'amount': amount}]},
                               format='json')


def test_sales_and_voids_move_the_ledger_at_the_same_cost(pos):
    recipe = pan_de_bono_recipe(pos).data
    pos['admin'].post(BATCHES, {'recipe': recipe['id'], 'quantity': '40'}, format='json')
    res = sell(pos, pos['pan'], '5', '11900')  # 5 × 2.000 + IVA 19 %
    assert res.status_code == 201, res.content
    sale = res.data
    assert item(pos, 'pan').stock == Decimal('35')
    with tenant_context(pos['t']):
        out = StockMovement.objects.get(type='sale')
        assert out.quantity == Decimal('-5') and out.source_label == f"Venta {sale['number']}"
    pos['admin'].post(f"/api/sales/{sale['id']}/void/", {'reason': 'Error'}, format='json')
    with tenant_context(pos['t']):
        back = StockMovement.objects.get(type='sale_void')
        assert back.quantity == Decimal('5') and back.unit_cost == out.unit_cost
    assert item(pos, 'pan').stock == Decimal('40')


def test_prepared_drinks_consume_their_recipe_when_sold(pos):
    res = pos['admin'].post(ITEMS, {'name': 'Tinto', 'kind': 'finished_good', 'price': '1800', 'tax_rate': '0',
                                    'consume_on_sale': True}, format='json')
    tinto = res.data['id']
    pos['admin'].post(RECIPES, {'product': tinto, 'yield_quantity': '20', 'lines': [
        {'ingredient': pos['cafe'], 'quantity': '100', 'unit': 'g'},
        {'ingredient': pos['vaso'], 'quantity': '20', 'unit': 'und'}]}, format='json')
    sale = sell(pos, tinto, '2', '3600')
    assert sale.status_code == 201, sale.content
    assert item(pos, 'cafe').stock == Decimal('1.99') and item(pos, 'vaso').stock == Decimal('98')
    with tenant_context(pos['t']):
        line = Item.objects.get(pk=tinto).sale_lines.get()
        assert line.unit_cost == Decimal('310')  # (0,01 kg × 38.000 + 2 × 120) / 2
        assert not StockMovement.objects.filter(item_id=tinto).exists()


# ── Mermas ──────────────────────────────────────────────────────────────────

def test_waste_leaves_inventory_at_current_cost(pos):
    recipe = pan_de_bono_recipe(pos).data
    pos['admin'].post(BATCHES, {'recipe': recipe['id'], 'quantity': '40'}, format='json')
    reasons = {r['code']: r['id'] for r in pos['cashier'].get('/api/waste/reasons/').data}
    assert {'unsold', 'burnt', 'expired'} <= reasons.keys()
    half = pos['cashier'].post('/api/waste/', {'item': pos['pan'], 'quantity': '1.5', 'reason': reasons['burnt']},
                               format='json')
    assert half.status_code == 400  # unidades enteras
    ok = pos['cashier'].post('/api/waste/', {'item': pos['pan'], 'quantity': '3', 'reason': reasons['burnt']},
                             format='json')
    assert ok.status_code == 201 and 'total_cost' not in ok.data  # el cajero no ve costos
    assert pos['cashier'].get('/api/waste/').status_code == 403  # registra, pero no consulta
    listing = pos['admin'].get('/api/waste/').data
    assert listing['total_cost'] == money(item(pos, 'pan').avg_cost * 3)
    assert item(pos, 'pan').stock == Decimal('37')


def money(value):
    return f'{Decimal(value).quantize(Decimal("0.01"))}'


def test_new_companies_get_waste_reasons_and_inventory_permissions(db):
    t = s.make_tenant('Nueva inventario')
    with tenant_context(t):
        roles = {r.code: set(r.permissions.values_list('code', flat=True)) for r in Role.objects.all()}
    assert {'inventory.adjust', 'purchases.create', 'recipes.manage', 'production.register'} <= roles['INVENTORY']
    assert 'waste.register' in roles['CASHIER'] and 'inventory.view' not in roles['CASHIER']
    assert UnitOfMeasure.objects.filter(code='arroba').exists()
