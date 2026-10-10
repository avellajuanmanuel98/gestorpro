"""Fase 9: analítica (períodos comparables, KPIs, rentabilidad, desgloses, CSV, atención) y producción sugerida."""
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from gestorpro.core.access.models import Role
from gestorpro.core.analytics.export import cell
from gestorpro.core.analytics.periods import change_pct, resolve
from gestorpro.core.cash.models import CashRegister, CashSession
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.sales.models import PaymentMethod, Sale
from gestorpro.core.tenancy.context import tenant_context
from tests import support as s

TZ = ZoneInfo('America/Bogota')


class FakeTenant:
    timezone = 'America/Bogota'


# ── Períodos ────────────────────────────────────────────────────────────────

def test_today_compares_with_the_same_weekday_last_week():
    p = resolve(FakeTenant(), 'today', today=date(2026, 10, 10))  # sábado
    assert (p.current.first, p.previous.first) == (date(2026, 10, 10), date(2026, 10, 3))
    assert p.previous.first.weekday() == 5


def test_month_to_date_compares_with_the_same_span_of_last_month():
    p = resolve(FakeTenant(), 'this_month', today=date(2026, 3, 31))
    assert (p.current.first, p.current.last) == (date(2026, 3, 1), date(2026, 3, 31))
    assert (p.previous.first, p.previous.last) == (date(2026, 2, 1), date(2026, 2, 28))
    last = resolve(FakeTenant(), 'last_month', today=date(2026, 1, 15))
    assert (last.current.first, last.current.last) == (date(2025, 12, 1), date(2025, 12, 31))


def test_custom_and_rolling_ranges():
    p = resolve(FakeTenant(), 'custom', '2026-10-01', '2026-10-05')
    assert p.current.days == 5 and (p.previous.first, p.previous.last) == (date(2026, 9, 26), date(2026, 9, 30))
    seven = resolve(FakeTenant(), '7d', today=date(2026, 10, 10))
    assert seven.current.first == date(2026, 10, 4) and seven.previous.last == date(2026, 10, 3)
    with pytest.raises(ValidationError):
        resolve(FakeTenant(), 'custom', '2026-10-05', '2026-10-01')
    with pytest.raises(ValidationError):
        resolve(FakeTenant(), 'forever')


def test_change_is_never_invented_without_a_base():
    assert change_pct(Decimal('100'), Decimal('0')) is None
    assert change_pct(Decimal('112'), Decimal('100')) == 12.0


def test_csv_cells_use_decimal_comma_and_neutralize_formulas():
    assert cell('13140.00') == '13140,00' and cell(-5) == '-5'
    assert cell('=HYPERLINK("http://x")') == '\'=HYPERLINK("http://x")'
    assert cell('+57 300') == "'+57 300" and cell('Pan de bono') == 'Pan de bono'


# ── Datos de ventas ─────────────────────────────────────────────────────────

@pytest.fixture
def shop(db):
    t = s.make_tenant('Analítica')
    owner = s.api_for(s.make_user(t, 'adm@ana.co', 'ADMIN'))
    sup_user = s.make_user(t, 'sup@ana.co', 'SUPERVISOR')
    with tenant_context(t):
        und = UnitOfMeasure.objects.get(code='und')
        register = CashRegister.objects.get()
        cash = PaymentMethod.objects.get(code='cash').id
        card = PaymentMethod.objects.get(code='card').id
        items = {name: Item.objects.create(name=name, code=name[:6].upper(), price=Decimal(price), tax_rate=0,
                                           avg_cost=Decimal(cost), unit=und)
                 for name, price, cost in [('Pan', '1000', '300'), ('Torta', '5000', '1000'),
                                           ('Galleta', '2000', '1500'), ('Gaseosa', '3000', '2500')]}
    supervisor = s.api_for(sup_user)
    supervisor.post('/api/cash/sessions/', {'register': register.id, 'opening_amount': '0'}, format='json')
    return {'t': t, 'owner': owner, 'sup': supervisor, 'items': items, 'cash': cash, 'card': card}


def sell(ctx, lines, when: datetime | None = None, method='cash'):
    body = {'client_uuid': str(uuid.uuid4()), 'lines': [{'item': ctx['items'][n].id, 'quantity': q} for n, q in lines],
            'payments': [{'method': ctx[method], 'amount': '999999' if method == 'cash' else None}]}
    if method != 'cash':
        total = sum(ctx['items'][n].price * Decimal(q) for n, q in lines)
        body['payments'][0]['amount'] = str(total)
    res = ctx['sup'].post('/api/sales/', body, format='json')
    assert res.status_code == 201, res.content
    if when:
        with tenant_context(ctx['t']):
            Sale.objects.filter(pk=res.data['id']).update(created_at=when)
    return res.data


def local(d: date, hour=12):
    return datetime.combine(d, time(hour), tzinfo=TZ)


def today():
    return timezone.now().astimezone(TZ).date()


def test_summary_kpis_compare_with_last_week_and_respect_permissions(shop):
    sell(shop, [('Pan', '10')])                                        # hoy: 10.000
    sell(shop, [('Torta', '2')])                                       # hoy: 10.000
    sell(shop, [('Pan', '8')], when=local(today() - timedelta(days=7)))  # mismo día semana pasada: 8.000
    data = shop['owner'].get('/api/analytics/summary/', {'period': 'today'}).data
    k = data['kpis']
    assert k['sales'] == {'value': '20000.00', 'previous': '8000.00', 'change_pct': 150.0}
    assert k['transactions']['value'] == 2 and k['average_ticket']['value'] == '10000.00'
    assert k['gross_profit']['value'] == '15000.00'  # 20.000 − (10×300 + 2×1.000)
    assert k['gross_margin_pct'] == 75.0
    with tenant_context(shop['t']):
        Role.objects.get(code='SUPERVISOR').permissions.remove('catalog.view_costs')
    sup = shop['sup'].get('/api/analytics/summary/').data['kpis']
    assert 'gross_profit' not in sup and 'cost_of_sales' not in sup
    cashier = s.api_for(s.make_user(shop['t'], 'caj@ana.co', 'CASHIER'))
    assert cashier.get('/api/analytics/summary/').status_code == 403


def test_products_report_profitability_waste_rate_and_quadrants(shop):
    sell(shop, [('Pan', '50'), ('Torta', '10'), ('Galleta', '3'), ('Gaseosa', '40')])
    rows = {r['name']: r for r in shop['owner'].get('/api/analytics/products/', {'period': 'today'}).data['rows']}
    assert rows['Pan']['units'] == '50.0000' and rows['Pan']['revenue'] == '50000.00'
    assert rows['Pan']['gross_profit'] == '35000.00' and rows['Pan']['margin_pct'] == 70.0
    quadrants = {name: r['quadrant'] for name, r in rows.items()}
    # Volumen mediano 25; margen unitario mediano 600 (Pan 700, Torta 4.000, Galleta 500, Gaseosa 500)
    assert quadrants == {'Pan': 'star', 'Gaseosa': 'workhorse', 'Torta': 'puzzle', 'Galleta': 'dog'}


def test_waste_rate_uses_produced_and_wasted_units(shop):
    owner = shop['owner']
    flour = owner.post('/api/catalog/items/', {'name': 'Harina', 'kind': 'raw_material', 'unit': 'kg',
                                               'avg_cost': '3000', 'stock': '50'}, format='json').data['id']
    recipe = owner.post('/api/production/recipes/', {'product': shop['items']['Pan'].id, 'yield_quantity': '100',
                                                     'lines': [{'ingredient': flour, 'quantity': '5'}]},
                        format='json').data
    owner.post('/api/production/batches/', {'recipe': recipe['id'], 'quantity': '100'}, format='json')
    reason = owner.get('/api/waste/reasons/').data[0]['id']
    owner.post('/api/waste/', {'item': shop['items']['Pan'].id, 'quantity': '8', 'reason': reason}, format='json')
    pan = next(r for r in owner.get('/api/analytics/products/').data['rows'] if r['name'] == 'Pan')
    assert pan['produced'] == '100.0000' and pan['wasted'] == '8.0000' and pan['waste_rate_pct'] == 8.0
    summary = owner.get('/api/waste/summary/', {'period': 'today'}).data
    assert summary['by_reason'][0]['records'] == 1 and summary['total_cost'] == '1200.00'  # 8 × 150


def test_breakdowns_and_hourly(shop):
    sell(shop, [('Pan', '2')], method='card')
    sell(shop, [('Torta', '1')], when=local(today(), 7))
    by_method = {r['label']: r['sales'] for r in shop['owner'].get('/api/analytics/breakdown/', {
        'period': 'today', 'by': 'method'}).data['rows']}
    assert by_method == {'Tarjeta': '2000.00', 'Efectivo': '5000.00'}
    hours = {h['hour']: h['sales'] for h in shop['owner'].get('/api/analytics/hourly/').data['hours']}
    assert hours[7] == '5000.00'
    assert shop['owner'].get('/api/analytics/breakdown/', {'by': 'planet'}).status_code == 400


def test_csv_export(shop):
    with tenant_context(shop['t']):
        Item.objects.filter(pk=shop['items']['Galleta'].pk).update(name='=cmd|calc')
    sell(shop, [('Galleta', '1')])
    res = shop['owner'].get('/api/analytics/products/', {'period': 'today', 'export': 'csv'})
    body = res.content.decode('utf-8')
    assert res['Content-Type'].startswith('text/csv') and body.startswith('﻿')
    assert "'=cmd|calc" in body and '2000,00' in body and 'Producto;Categoría' in body


def test_attention_flags_real_problems(shop):
    with tenant_context(shop['t']):
        Item.objects.filter(pk=shop['items']['Pan'].pk).update(stock=-5)
        Item.objects.filter(pk=shop['items']['Torta'].pk).update(stock=2, minimum_stock=5)
        CashSession.objects.update(opened_at=timezone.now() - timedelta(hours=14))
    kinds = {a['kind'] for a in shop['owner'].get('/api/analytics/summary/').data['attention']}
    assert kinds == {'negative_stock', 'low_stock', 'stale_cash'}


def test_cash_report_requires_cash_manage(shop):
    cashier = s.api_for(s.make_user(shop['t'], 'caj2@ana.co', 'CASHIER'))
    assert cashier.get('/api/analytics/cash/').status_code == 403
    assert shop['owner'].get('/api/analytics/cash/', {'period': 'today'}).data['sessions']


# ── Producción sugerida (Miga) ──────────────────────────────────────────────

@pytest.fixture
def bakery(db):
    from gestorpro.core.access.services import provision_tenant
    t = provision_tenant(name='Panadería Sugerida', vertical='bakery', plan_code='pro')
    return {'t': t}


def test_production_suggestion_uses_same_weekday_history_and_batches(shop):
    with tenant_context(shop['t']):
        shop['t'].vertical = 'bakery'
        shop['t'].save(update_fields=['vertical'])
    target = today() + timedelta(days=1)
    for weeks, qty in [(1, '40'), (2, '50'), (3, '45')]:
        sell(shop, [('Pan', qty)], when=local(target - timedelta(weeks=weeks)))
    owner = shop['owner']
    flour = owner.post('/api/catalog/items/', {'name': 'Harina', 'kind': 'raw_material', 'unit': 'kg',
                                               'avg_cost': '3000', 'stock': '50'}, format='json').data['id']
    owner.post('/api/production/recipes/', {'product': shop['items']['Pan'].id, 'yield_quantity': '20',
                                            'lines': [{'ingredient': flour, 'quantity': '1'}]}, format='json')
    with tenant_context(shop['t']):
        Item.objects.filter(pk=shop['items']['Pan'].pk).update(stock=10)
    data = owner.get('/api/bakery/production-suggestion/').data
    pan = next(r for r in data['rows'] if r['name'] == 'Pan')
    assert data['weeks_with_data'] == 3 and pan['average_sold'] == '45.0'
    # Faltan 45 − 10 = 35 → 2 tandas de 20 = 40
    assert pan['batches'] == 2 and pan['suggested'] == '40'


def test_suggestion_needs_enough_history_and_is_bakery_only(shop, bakery):
    with tenant_context(shop['t']):
        shop['t'].vertical = 'bakery'
        shop['t'].save(update_fields=['vertical'])
    sell(shop, [('Pan', '40')], when=local(today() + timedelta(days=1) - timedelta(weeks=1)))
    data = shop['owner'].get('/api/bakery/production-suggestion/').data
    assert data['weeks_with_data'] == 1 and data['rows'] == []
    generic = s.api_for(s.make_user(s.make_tenant('Ferretería Analítica'), 'adm@fer2.co', 'ADMIN'))
    assert generic.get('/api/bakery/production-suggestion/').status_code == 404


def test_voided_sales_are_not_counted(shop):
    sell(shop, [('Pan', '10')])
    voided = sell(shop, [('Torta', '3')])
    assert shop['owner'].post(f"/api/sales/{voided['id']}/void/", {'reason': 'Error de digitación'},
                              format='json').status_code == 200
    k = shop['owner'].get('/api/analytics/summary/', {'period': 'today'}).data['kpis']
    assert k['sales']['value'] == '10000.00' and k['transactions']['value'] == 1
    assert k['cost_of_sales']['value'] == '3000.00'
    names = {r['name'] for r in shop['owner'].get('/api/analytics/products/').data['rows']}
    assert names == {'Pan'}


def test_coverage_days_from_last_30_days_usage(shop):
    owner = shop['owner']
    flour = owner.post('/api/catalog/items/', {'name': 'Harina', 'kind': 'raw_material', 'unit': 'kg',
                                               'avg_cost': '3000', 'stock': '45'}, format='json').data['id']
    recipe = owner.post('/api/production/recipes/', {'product': shop['items']['Pan'].id, 'yield_quantity': '10',
                                                     'lines': [{'ingredient': flour, 'quantity': '3'}]},
                        format='json').data
    owner.post('/api/production/batches/', {'recipe': recipe['id'], 'quantity': '10'}, format='json')
    rows = owner.get('/api/analytics/coverage/').data['rows']
    assert rows == [{'item': flour, 'name': 'Harina', 'unit': 'kg', 'stock': '42.0000', 'daily_usage': '0.100',
                     'days_left': 420.0}]  # 3 kg en 30 días → 0,1 kg/día; 42 kg alcanzan para 420 días
    cashier = s.api_for(s.make_user(shop['t'], 'caj2@ana.co', 'CASHIER'))
    assert cashier.get('/api/analytics/coverage/').status_code == 403
