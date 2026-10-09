"""Fase 6: unidades de medida, productos e ingredientes, costos y catálogo base de panadería."""
import io
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command

from gestorpro.core.catalog.models import Category, Item, UnitOfMeasure
from gestorpro.core.tenancy.context import tenant_context
from gestorpro.kernel import units
from tests import support as s

ITEMS = s.ENDPOINTS['products']
KG = units.Unit('kg', units.Dimension.MASS, Decimal('1000'))
G = units.Unit('g', units.Dimension.MASS, Decimal('1'))
LB = units.Unit('lb', units.Dimension.MASS, Decimal('500'))
L = units.Unit('l', units.Dimension.VOLUME, Decimal('1000'))
UND = units.Unit('und', units.Dimension.COUNT, Decimal('1'))
DOCENA = units.Unit('docena', units.Dimension.COUNT, Decimal('12'))


# ── Conversión de unidades (kernel, sin base de datos) ────────────────────────

def test_conversion_within_a_dimension():
    assert units.convert('1.5', KG, G) == Decimal('1500')
    assert units.convert('250', G, KG) == Decimal('0.25')
    assert units.convert('3', LB, KG) == Decimal('1.5')  # libra colombiana = 500 g
    assert units.convert('2', DOCENA, UND) == Decimal('24')
    assert units.convert('1', G, KG) == Decimal('0.001')


def test_conversion_between_dimensions_is_rejected():
    with pytest.raises(units.IncompatibleUnits):
        units.convert('1', KG, L)
    with pytest.raises(units.IncompatibleUnits):
        units.cost_per('3200', KG, UND)


def test_quantities_reject_float_and_round_to_four_decimals():
    with pytest.raises(TypeError):
        units.quantity(0.1)
    assert units.quantity('0.33335') == Decimal('0.3334')


def test_cost_is_reexpressed_per_unit_without_rounding_to_cents():
    assert units.cost_per('3200', KG, G) == Decimal('3.2')
    assert units.cost_per('560', UND, DOCENA) == Decimal('6720')


@pytest.mark.django_db
def test_seeded_units_match_the_kernel_factors():
    assert UnitOfMeasure.objects.get(code='lb').as_unit().factor == Decimal('500')
    assert set(UnitOfMeasure.objects.values_list('code', flat=True)) >= {'g', 'kg', 'lb', 'ml', 'l', 'und', 'docena'}


# ── Reglas de ítems en el backend ────────────────────────────────────────────

@pytest.fixture
def ctx(db):
    t = s.make_tenant('Catálogo')
    with tenant_context(t):
        ingredients = Category.objects.create(name='Harinas', kind=Category.Kind.INGREDIENT)
        breads = Category.objects.create(name='Panes', kind=Category.Kind.PRODUCT)
    return {
        't': t, 'ingredients': ingredients, 'breads': breads,
        'admin': s.api_for(s.make_user(t, 'adm@cat.co', 'ADMIN')),
        'cashier': s.api_for(s.make_user(t, 'caj@cat.co', 'CASHIER')),
        }


def ingredient(**kw):
    data = {'name': 'Harina de trigo', 'kind': 'raw_material', 'unit': 'kg', 'avg_cost': '3200',
            'stock': '85', 'minimum_stock': '50'}
    data.update(kw)
    return data


def test_ingredient_ignores_sale_price_and_gets_an_automatic_code(ctx):
    res = ctx['admin'].post(ITEMS, ingredient(price='9999', tax_rate='19', category=ctx['ingredients'].id),
                            format='json')
    assert res.status_code == 201, res.content
    assert res.data['code'] == 'ING-0001' and res.data['price'] == '0.00' and res.data['tax_rate'] == '0.00'
    assert res.data['unit'] == 'kg' and res.data['is_sellable'] is False
    assert res.data['stock_value'] == '272000.00'  # 85 kg × $3.200
    second = ctx['admin'].post(ITEMS, ingredient(name='Azúcar'), format='json')
    assert second.data['code'] == 'ING-0002'


def test_ingredient_can_also_be_sold_with_a_price(ctx):
    res = ctx['admin'].post(ITEMS, ingredient(name='Queso costeño', is_sellable=True, price='26000',
                                              avg_cost='20000'), format='json')
    assert res.status_code == 201, res.content
    assert res.data['margin_pct'] == '23.1'


def test_products_require_a_price_and_are_always_sellable(ctx):
    res = ctx['admin'].post(ITEMS, {'name': 'Pan francés', 'kind': 'finished_good'}, format='json')
    assert res.status_code == 400 and 'price' in res.data
    res = ctx['admin'].post(ITEMS, {'name': 'Pan francés', 'kind': 'finished_good', 'price': '1500',
                                    'is_sellable': False}, format='json')
    assert res.status_code == 201 and res.data['is_sellable'] is True
    assert res.data['code'] == 'PRD-0001' and res.data['unit'] == 'und'


def test_services_have_no_stock_and_are_sold_by_unit(ctx):
    res = ctx['admin'].post(ITEMS, {'name': 'Domicilio', 'kind': 'service', 'price': '4000', 'stock': '10',
                                    'avg_cost': '500'}, format='json')
    assert res.status_code == 201, res.content
    assert res.data['stock'] == '0.0000' and res.data['avg_cost'] == '0.0000' and res.data['code'] == 'SRV-0001'
    res = ctx['admin'].post(ITEMS, {'name': 'Domicilio 2', 'kind': 'service', 'price': '4000', 'unit': 'kg'},
                            format='json')
    assert res.status_code == 400 and 'unit' in res.data


def test_category_must_match_the_item_kind(ctx):
    res = ctx['admin'].post(ITEMS, ingredient(category=ctx['breads'].id), format='json')
    assert res.status_code == 400 and 'category' in res.data
    res = ctx['admin'].post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500',
                                    'category': ctx['ingredients'].id}, format='json')
    assert res.status_code == 400 and 'category' in res.data


def test_unknown_unit_is_rejected(ctx):
    res = ctx['admin'].post(ITEMS, ingredient(unit='taza'), format='json')
    assert res.status_code == 400 and 'unit' in res.data


def test_groups_split_products_and_ingredients(ctx):
    ctx['admin'].post(ITEMS, ingredient(), format='json')
    ctx['admin'].post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500'}, format='json')
    ctx['admin'].post(ITEMS, {'name': 'Gaseosa', 'kind': 'resale', 'price': '3200'}, format='json')
    names = lambda group: {i['name'] for i in s.results(ctx['admin'].get(ITEMS, {'group': group}))}  # noqa: E731
    assert names('ingredients') == {'Harina de trigo'}
    assert names('products') == {'Pan', 'Gaseosa'}


def test_low_stock_includes_ingredients_with_their_unit(ctx):
    ctx['admin'].post(ITEMS, ingredient(stock='12', minimum_stock='50'), format='json')
    ctx['admin'].post(ITEMS, ingredient(name='Sal', stock='10', minimum_stock='0'), format='json')  # sin mínimo
    low = s.results(ctx['admin'].get('/api/catalog/low-stock/'))
    assert [(i['name'], i['unit_symbol']) for i in low] == [('Harina de trigo', 'kg')]


# ── Costos: información sensible ─────────────────────────────────────────────

def test_cashier_does_not_see_costs_or_margins(ctx):
    ctx['admin'].post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500', 'avg_cost': '500'},
                      format='json')
    admin_row = s.results(ctx['admin'].get(ITEMS))[0]
    cashier_row = s.results(ctx['cashier'].get(ITEMS))[0]
    assert admin_row['avg_cost'] == '500.0000' and admin_row['margin_pct'] == '66.7'
    assert not {'avg_cost', 'margin_pct', 'stock_value'} & cashier_row.keys()
    detail = ctx['cashier'].get(f"{ITEMS}{cashier_row['id']}/").data
    assert 'avg_cost' not in detail


def test_managing_the_catalog_without_cost_permission_cannot_set_costs(ctx):
    from gestorpro.core.access.models import Role
    with tenant_context(ctx['t']):
        role = Role.objects.get(code='INVENTORY')
        role.permissions.remove('catalog.view_costs')
    api = s.api_for(s.make_user(ctx['t'], 'inv@cat.co', 'INVENTORY'))
    res = api.post(ITEMS, ingredient(), format='json')
    assert res.status_code == 403
    ok = api.post(ITEMS, {k: v for k, v in ingredient(name='Sal').items() if k != 'avg_cost'}, format='json')
    assert ok.status_code == 201 and 'avg_cost' not in ok.data


def test_inventory_report_values_stock_at_cost_and_hides_it_without_permission(ctx):
    ctx['admin'].post(ITEMS, ingredient(), format='json')  # 85 kg × 3.200 = 272.000
    ctx['admin'].post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500', 'avg_cost': '500',
                              'stock': '40'}, format='json')  # 40 × 500 = 20.000 (no a precio de venta)
    data = ctx['admin'].get(s.ENDPOINTS['report_inventory']).data
    assert data['valor_ingredientes'] == '272000.00' and data['valor_productos'] == '20000.00'
    assert data['valor_inventario'] == '292000.00' and data['valor_inventario_base'] == 'cost'
    assert data['total_productos'] == 1 and data['total_ingredientes'] == 1

    from gestorpro.core.access.models import Role
    with tenant_context(ctx['t']):
        Role.objects.get(code='SUPERVISOR').permissions.remove('catalog.view_costs')
    supervisor = s.api_for(s.make_user(ctx['t'], 'sup@cat.co', 'SUPERVISOR'))
    data = supervisor.get(s.ENDPOINTS['report_inventory']).data
    assert data['valor_inventario'] is None and all(r['valor'] is None for r in data['by_category'])


# ── Integración con facturación y límites del plan ───────────────────────────

def test_ingredients_that_are_not_sold_cannot_be_invoiced(ctx):
    item_id = ctx['admin'].post(ITEMS, ingredient(), format='json').data['id']
    customer = s.make_customer(ctx['t'])
    res = ctx['admin'].post(s.ENDPOINTS['invoices'], s.invoice_payload(customer.id, item_id, unit_price='0'),
                            format='json')
    assert res.status_code == 400 and 'ingrediente' in str(res.data)


def test_ingredients_do_not_consume_the_products_limit(ctx):
    from gestorpro.core.catalog.services import products_count
    ctx['admin'].post(ITEMS, ingredient(), format='json')
    ctx['admin'].post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500'}, format='json')
    with tenant_context(ctx['t']):
        assert products_count() == 1
    limits = {r['key']: r['used'] for r in ctx['admin'].get('/api/tenant/plan/').data['limits']}
    assert limits['products'] == 1


def test_products_limit_blocks_new_products_but_not_ingredients(db):
    t = s.make_tenant('Limitada', plan_code='starter')
    api = s.api_for(s.make_user(t, 'adm@lim.co', 'ADMIN'))
    from gestorpro.platform.subscriptions.models import PlanLimit
    PlanLimit.objects.filter(plan__code='starter', key='products').update(value=1)
    assert api.post(ITEMS, {'name': 'Pan', 'kind': 'finished_good', 'price': '1500'}, format='json').status_code == 201
    assert api.post(ITEMS, {'name': 'Pan 2', 'kind': 'finished_good', 'price': '1500'},
                    format='json').status_code == 403
    assert api.post(ITEMS, ingredient(), format='json').status_code == 201


# ── Vertical Miga: alta y catálogo base ─────────────────────────────────────

def test_bakery_provisioning_creates_categories_and_final_consumer(db):
    from gestorpro.core.access.services import provision_tenant
    from gestorpro.core.customers.models import Customer
    tenant = provision_tenant(name='Panadería Nueva', vertical='bakery')
    with tenant_context(tenant):
        assert Category.objects.filter(kind=Category.Kind.PRODUCT, name='Panes').exists()
        assert Category.objects.filter(kind=Category.Kind.INGREDIENT, name='Empaques').exists()
        assert Customer.objects.get(document_number='222222222222').full_name == 'Consumidor final'
        assert not Item.objects.exists()


def test_starter_catalog_is_idempotent_and_has_no_costs(db):
    from gestorpro.core.access.services import provision_tenant
    tenant = provision_tenant(name='Panadería La Favorita', vertical='bakery')
    out = io.StringIO()
    call_command('load_starter_catalog', tenant.slug, stdout=out)
    with tenant_context(tenant):
        created = Item.objects.count()
        assert created >= 30 and 'ingredientes creados' in out.getvalue()
        assert not Item.objects.exclude(kind=Item.Kind.RAW_MATERIAL).exists()
        assert not Item.objects.filter(avg_cost__gt=0).exists() and not Item.objects.filter(stock__gt=0).exists()
        assert Item.objects.get(name='Huevos').unit.code == 'und'
        Item.objects.filter(name='Huevos').update(avg_cost=560)  # la panadería registra su costo
    call_command('load_starter_catalog', tenant.slug, stdout=io.StringIO())
    with tenant_context(tenant):
        assert Item.objects.count() == created
        assert Item.objects.get(name='Huevos').avg_cost == 560


def test_starter_catalog_only_for_bakeries(db):
    from gestorpro.core.access.services import provision_tenant
    tenant = provision_tenant(name='Ferretería', vertical='generic')
    with pytest.raises(CommandError):
        call_command('load_starter_catalog', tenant.slug, stdout=io.StringIO())


def test_owner_can_load_the_starter_catalog_from_the_app(db):
    from gestorpro.core.access.services import provision_tenant
    bakery = provision_tenant(name='Panadería Web', vertical='bakery')
    admin = s.api_for(s.make_user(bakery, 'adm@web.co', 'ADMIN'))
    res = admin.post('/api/bakery/starter-catalog/')
    assert res.status_code == 200 and res.data['created'] >= 30
    assert admin.post('/api/bakery/starter-catalog/').data['created'] == 0
    cashier = s.api_for(s.make_user(bakery, 'caj@web.co', 'CASHIER'))
    assert cashier.post('/api/bakery/starter-catalog/').status_code == 403

    generic = s.api_for(s.make_user(s.make_tenant('Ferretería Web'), 'adm@fer.co', 'ADMIN'))
    assert generic.post('/api/bakery/starter-catalog/').status_code == 404
