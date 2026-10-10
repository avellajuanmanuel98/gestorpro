"""
Consultas de analítica sobre datos REALES (ventas, caja e inventario). Ninguna
cifra se inventa: si no hay base de comparación, la variación es None ("—").

Definiciones (también en docs/miga/08-fase-9-analitica.md):
- Ventas = Σ total cobrado (con IVA, después de descuentos) de ventas completadas.
- Ingreso sin IVA = Σ (total − IVA).
- Costo de ventas = Σ costo congelado en cada venta (promedio ponderado al vender).
- Utilidad bruta = ingreso sin IVA − costo de ventas.
- Ticket promedio = ventas / número de ventas.
- Merma = costo de los movimientos de merma (al costo del momento).
- Tasa de merma de un producto = unidades perdidas / unidades producidas.
"""
from collections import defaultdict
from decimal import Decimal
from statistics import median

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, ExtractHour, ExtractIsoWeekDay, TruncDate
from django.utils import timezone

from gestorpro.core.cash.models import CashSession
from gestorpro.core.catalog.models import Item
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.sales.models import Payment, Sale, SaleLine
from gestorpro.kernel.money import ZERO, money

from .periods import Range, change_pct

DEC = DecimalField(max_digits=20, decimal_places=4)
WEEKDAY_NAMES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def _sales(r: Range, location=None):
    qs = Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__gte=r.start, created_at__lt=r.end)
    return qs.filter(location=location) if location else qs


def _movements(r: Range, location=None):
    qs = StockMovement.objects.filter(created_at__gte=r.start, created_at__lt=r.end)
    return qs.filter(location=location) if location else qs


def sales_totals(r: Range, location=None) -> dict:
    agg = _sales(r, location).aggregate(
        total=Coalesce(Sum('total'), ZERO, output_field=DEC), count=Count('id'),
        tax=Coalesce(Sum('tax_total'), ZERO, output_field=DEC),
        cost=Coalesce(Sum('cost_total'), ZERO, output_field=DEC))
    waste = _movements(r, location).filter(type=StockMovement.Type.WASTE).aggregate(
        t=Coalesce(Sum('total_cost'), ZERO, output_field=DEC))['t']
    net = agg['total'] - agg['tax']
    return {
        'sales': money(agg['total']), 'transactions': agg['count'],
        'average_ticket': money(agg['total'] / agg['count']) if agg['count'] else None,
        'net_revenue': money(net), 'cost_of_sales': money(agg['cost']), 'gross_profit': money(net - agg['cost']),
        'waste_cost': money(-waste),
    }


def kpis(period, location=None, show_costs=False) -> dict:
    cur, prev = sales_totals(period.current, location), sales_totals(period.previous, location)
    keys = ['sales', 'transactions', 'average_ticket'] + (['gross_profit', 'cost_of_sales', 'waste_cost']
                                                           if show_costs else [])
    out = {}
    for key in keys:
        out[key] = {'value': _s(cur[key]), 'previous': _s(prev[key]), 'change_pct': change_pct(cur[key], prev[key])}
    if show_costs:
        margin = (cur['gross_profit'] / cur['net_revenue'] * 100) if cur['net_revenue'] else None
        out['gross_margin_pct'] = round(float(margin), 1) if margin is not None else None
        base = cur['cost_of_sales'] + cur['waste_cost']
        out['waste_pct_of_cost'] = round(float(cur['waste_cost'] / base * 100), 1) if base else None
    return out


def _s(value):
    return None if value is None else (str(value) if isinstance(value, Decimal) else value)


def by_hour(period, location=None) -> list[dict]:
    """Ventas por hora del período y del comparable (promedio por día si el período tiene varios días)."""
    def series(r: Range):
        rows = (_sales(r, location).annotate(h=ExtractHour('created_at', tzinfo=r.tz)).values('h')
                .annotate(total=Sum('total'), n=Count('id')))
        return {row['h']: (row['total'] / r.days, row['n']) for row in rows}
    cur, prev = series(period.current), series(period.previous)
    hours = sorted(set(cur) | set(prev)) or list(range(6, 21))
    return [{'hour': h, 'sales': str(money(cur.get(h, (ZERO, 0))[0])), 'transactions': cur.get(h, (0, 0))[1],
             'previous_sales': str(money(prev.get(h, (ZERO, 0))[0]))}
            for h in range(min(hours), max(hours) + 1)]


def breakdown(period, by: str, location=None) -> list[dict]:
    r = period.current
    sales = _sales(r, location)
    if by == 'day':
        rows = sales.annotate(k=TruncDate('created_at', tzinfo=r.tz)).values('k').annotate(
            total=Sum('total'), n=Count('id')).order_by('k')
        return [{'key': row['k'].isoformat(), 'label': row['k'].strftime('%d/%m'), 'sales': str(row['total']),
                 'transactions': row['n']} for row in rows]
    if by == 'weekday':
        rows = sales.annotate(k=ExtractIsoWeekDay('created_at', tzinfo=r.tz)).values('k').annotate(
            total=Sum('total'), n=Count('id')).order_by('k')
        return [{'key': row['k'], 'label': WEEKDAY_NAMES[row['k'] - 1], 'sales': str(row['total']),
                 'transactions': row['n']} for row in rows]
    if by == 'method':
        rows = (Payment.objects.filter(sale__in=sales).values('method__name').annotate(total=Sum('amount'),
                                                                                       n=Count('sale', distinct=True))
                .order_by('-total'))
        return [{'key': row['method__name'], 'label': row['method__name'], 'sales': str(row['total']),
                 'transactions': row['n']} for row in rows]
    if by == 'cashier':
        rows = (sales.values('cashier__first_name', 'cashier__last_name', 'cashier__email')
                .annotate(total=Sum('total'), n=Count('id')).order_by('-total'))
        return [{'key': row['cashier__email'],
                 'label': f"{row['cashier__first_name']} {row['cashier__last_name']}".strip() or row['cashier__email'],
                 'sales': str(row['total']), 'transactions': row['n']} for row in rows]
    if by == 'category':
        rows = (SaleLine.objects.filter(sale__in=sales).values('item__category__name')
                .annotate(total=Sum('line_total'), n=Count('sale', distinct=True)).order_by('-total'))
        return [{'key': row['item__category__name'] or '—', 'label': row['item__category__name'] or 'Sin categoría',
                 'sales': str(row['total']), 'transactions': row['n']} for row in rows]
    raise ValueError(by)


QUADRANTS = {
    (True, True): ('star', 'Estrella', 'Se vende mucho y deja buen margen: cuídalo y destácalo.'),
    (True, False): ('workhorse', 'Caballo de batalla', 'Se vende mucho pero deja poco: revisa costo o precio.'),
    (False, True): ('puzzle', 'Enigma', 'Deja buen margen pero se vende poco: promociónalo o muévelo de lugar.'),
    (False, False): ('dog', 'Perro', 'Se vende poco y deja poco: considera reformularlo o retirarlo.'),
}


def products(period, location=None, show_costs=False) -> list[dict]:
    r = period.current
    line_cost = ExpressionWrapper(F('unit_cost') * F('quantity'), output_field=DEC)
    sold = {row['item']: row for row in SaleLine.objects.filter(sale__in=_sales(r, location)).values('item').annotate(
        units=Sum('quantity'), revenue=Sum('line_subtotal'), cost=Sum(line_cost))}
    moves = defaultdict(lambda: {'produced': ZERO, 'wasted': ZERO})
    kinds = [StockMovement.Type.PRODUCTION_OUTPUT, StockMovement.Type.WASTE]
    for row in _movements(r, location).filter(type__in=kinds).values('item', 'type').annotate(q=Sum('quantity')):
        key = 'produced' if row['type'] == StockMovement.Type.PRODUCTION_OUTPUT else 'wasted'
        moves[row['item']][key] = abs(row['q'])
    ids = set(sold) | {i for i, m in moves.items() if m['produced'] or m['wasted']}
    items = {i.id: i for i in Item.objects.select_related('unit', 'category').filter(id__in=ids)
             .exclude(kind=Item.Kind.RAW_MATERIAL, is_sellable=False)}
    rows = []
    for item_id, item in items.items():
        s = sold.get(item_id, {'units': ZERO, 'revenue': ZERO, 'cost': ZERO})
        m = moves[item_id]
        units, revenue, cost = s['units'] or ZERO, s['revenue'] or ZERO, s['cost'] or ZERO
        row = {'item': item_id, 'name': item.name, 'category': item.category.name if item.category else None,
               'unit': item.unit.symbol, 'units': str(units), 'revenue': str(money(revenue)),
               'produced': str(m['produced']), 'wasted': str(m['wasted']),
               'waste_rate_pct': round(float(m['wasted'] / m['produced'] * 100), 1) if m['produced'] else None}
        if show_costs:
            profit = revenue - cost
            row.update(cost=str(money(cost)), gross_profit=str(money(profit)),
                       margin_pct=round(float(profit / revenue * 100), 1) if revenue else None,
                       unit_margin=str(money(profit / units)) if units else None)
        rows.append(row)
    if show_costs:
        _classify(rows)
    return sorted(rows, key=lambda x: Decimal(x['revenue']), reverse=True)


def _classify(rows: list[dict]) -> None:
    """Matriz volumen × margen (ingeniería de menú). Necesita al menos 4 productos con ventas y costo."""
    eligible = [r for r in rows if Decimal(r['units']) > 0 and r.get('unit_margin') is not None
                and Decimal(r['cost']) > 0]
    if len(eligible) < 4:
        return
    vol_cut = median(Decimal(r['units']) for r in eligible)
    margin_cut = median(Decimal(r['unit_margin']) for r in eligible)
    for r in eligible:
        code, label, advice = QUADRANTS[(Decimal(r['units']) >= vol_cut, Decimal(r['unit_margin']) >= margin_cut)]
        r.update(quadrant=code, quadrant_label=label, quadrant_advice=advice)


def cash_sessions(period, location=None) -> dict:
    r = period.current
    qs = CashSession.objects.filter(opened_at__gte=r.start, opened_at__lt=r.end).select_related(
        'register', 'opened_by', 'closed_by')
    if location:
        qs = qs.filter(register__location=location)
    sessions = [{'id': s.id, 'register': s.register.name, 'cashier': s.opened_by.full_name or s.opened_by.email,
                 'opened_at': s.opened_at.isoformat(), 'closed_at': s.closed_at.isoformat() if s.closed_at else None,
                 'status': s.status, 'expected': str(s.expected_amount) if s.expected_amount is not None else None,
                 'counted': str(s.counted_amount) if s.counted_amount is not None else None,
                 'difference': str(s.difference) if s.difference is not None else None, 'note': s.closing_note}
                for s in qs.order_by('-opened_at')]
    by_cashier = defaultdict(lambda: {'sessions': 0, 'with_difference': 0, 'net_difference': ZERO})
    for s in qs.filter(status=CashSession.Status.CLOSED):
        c = by_cashier[s.opened_by.full_name or s.opened_by.email]
        c['sessions'] += 1
        c['with_difference'] += int(s.difference != 0)
        c['net_difference'] += s.difference
    return {'sessions': sessions,
            'by_cashier': [{'cashier': k, 'sessions': v['sessions'], 'with_difference': v['with_difference'],
                            'net_difference': str(v['net_difference'])} for k, v in by_cashier.items()]}


def coverage(days: int = 30) -> list[dict]:
    """Días de cobertura: existencia / consumo diario promedio de los últimos `days` días (ingredientes)."""
    since = timezone.now() - timezone.timedelta(days=days)
    out_types = [StockMovement.Type.PRODUCTION_CONSUME, StockMovement.Type.SALE, StockMovement.Type.WASTE]
    usage = {row['item']: abs(row['q']) for row in StockMovement.objects.filter(
        created_at__gte=since, type__in=out_types, item__kind=Item.Kind.RAW_MATERIAL).values('item').annotate(
        q=Sum('quantity'))}
    rows = []
    for item in Item.objects.select_related('unit').filter(id__in=usage, is_active=True):
        daily = usage[item.id] / days
        rows.append({'item': item.id, 'name': item.name, 'unit': item.unit.symbol, 'stock': str(item.stock),
                     'daily_usage': str(daily.quantize(Decimal('0.001'))),
                     'days_left': round(float(item.stock / daily), 1) if daily > 0 and item.stock > 0 else 0.0})
    return sorted(rows, key=lambda x: x['days_left'])


def attention(show_costs: bool) -> list[dict]:
    """Lo que hay que hacer hoy, con datos reales."""
    items = []
    stocked = Item.objects.filter(is_active=True).exclude(kind=Item.Kind.SERVICE).exclude(consume_on_sale=True)
    low = stocked.filter(minimum_stock__gt=0, stock__lte=F('minimum_stock'), stock__gt=0)
    if low.exists():
        names = list(low.order_by('stock').values_list('name', flat=True)[:3])
        items.append({'kind': 'low_stock', 'tone': 'warning', 'count': low.count(), 'detail': ', '.join(names),
                      'to': '/ingredients' if not low.exclude(kind=Item.Kind.RAW_MATERIAL).exists() else '/inventory'})
    negative = stocked.filter(stock__lt=0)
    if negative.exists():
        items.append({'kind': 'negative_stock', 'tone': 'danger', 'count': negative.count(),
                      'detail': ', '.join(negative.values_list('name', flat=True)[:3]), 'to': '/production'})
    stale = CashSession.objects.filter(status=CashSession.Status.OPEN,
                                       opened_at__lt=timezone.now() - timezone.timedelta(hours=12))
    if stale.exists():
        items.append({'kind': 'stale_cash', 'tone': 'warning', 'count': stale.count(),
                      'detail': ', '.join(f'{s.register.name} ({s.opened_by.full_name or s.opened_by.email})'
                                          for s in stale.select_related('register', 'opened_by')[:3]), 'to': '/cash'})
    return items

