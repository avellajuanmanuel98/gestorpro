"""
Producción sugerida (exclusiva de Miga).

Para el día objetivo (por defecto, mañana) mira las últimas 4 semanas del
MISMO día de la semana (un sábado se compara con sábados) y, por producto
elaborado:

    promedio vendido = Σ unidades vendidas / semanas con la panadería abierta
    sugerido         = promedio vendido − existencia actual (nunca negativo),
                       redondeado hacia arriba a tandas completas de la receta

Una semana cuenta solo si ese día hubo ventas (la panadería estuvo abierta),
para no promediar contra días cerrados. Con menos de 2 semanas de historia
no se sugiere nada: se dice que faltan datos, nunca se inventa un número.
"""
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from gestorpro.capabilities.production.models import Recipe
from gestorpro.core.catalog.models import Item
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.sales.models import Sale, SaleLine

WEEKS = 4
MIN_WEEKS = 2


def _plain(value):
    """Decimal sin ceros sobrantes ni notación científica ('40', no '4E+1')."""
    return format(value.normalize(), 'f')


def suggest(tenant, target: date | None = None) -> dict:
    tz = ZoneInfo(tenant.timezone)
    today = timezone.now().astimezone(tz).date()
    target = target or today + timedelta(days=1)
    days = [target - timedelta(weeks=w) for w in range(1, WEEKS + 1) if target - timedelta(weeks=w) <= today]
    bounds = [(datetime.combine(d, time.min, tzinfo=tz), datetime.combine(d + timedelta(days=1), time.min, tzinfo=tz))
              for d in days]
    if not bounds:
        return {'target': target.isoformat(), 'weeks_with_data': 0, 'rows': []}

    window = Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__gte=min(b[0] for b in bounds),
                                 created_at__lt=max(b[1] for b in bounds))
    open_days = {d for d in window.annotate(d=TruncDate('created_at', tzinfo=tz)).values_list('d', flat=True)
                 if d in days}
    if len(open_days) < MIN_WEEKS:
        return {'target': target.isoformat(), 'weeks_with_data': len(open_days), 'rows': []}

    sold = defaultdict(dict)
    for row in (SaleLine.objects.filter(sale__in=window).annotate(d=TruncDate('sale__created_at', tzinfo=tz))
                .values('item', 'd').annotate(q=Sum('quantity'))):
        if row['d'] in open_days:
            sold[row['item']][row['d']] = row['q']
    wasted = defaultdict(lambda: Decimal('0'))
    for row in (StockMovement.objects.filter(type=StockMovement.Type.WASTE, created_at__gte=min(b[0] for b in bounds),
                                             created_at__lt=max(b[1] for b in bounds))
                .annotate(d=TruncDate('created_at', tzinfo=tz)).values('item', 'd').annotate(q=Sum('quantity'))):
        if row['d'] in open_days:
            wasted[row['item']] += abs(row['q'])

    recipes = {r.product_id: r for r in Recipe.objects.filter(is_active=True)}
    items = Item.objects.select_related('unit').filter(
        kind=Item.Kind.FINISHED_GOOD, is_active=True, consume_on_sale=False, id__in=sold.keys())
    weeks = len(open_days)
    rows = []
    for item in items:
        history = [sold[item.id].get(d, Decimal('0')) for d in sorted(open_days, reverse=True)]
        avg = sum(history, Decimal('0')) / weeks
        need = max(Decimal('0'), avg - max(item.stock, Decimal('0')))
        recipe = recipes.get(item.id)
        batches = math.ceil(need / recipe.yield_quantity) if recipe and need > 0 else None
        suggested = (recipe.yield_quantity * batches) if batches else Decimal(math.ceil(need))
        rows.append({
            'item': item.id, 'name': item.name, 'unit': item.unit.symbol,
            'history': [_plain(h) for h in history], 'average_sold': str(avg.quantize(Decimal('0.1'))),
            'average_wasted': str((wasted[item.id] / weeks).quantize(Decimal('0.1'))),
            'stock': _plain(item.stock), 'suggested': _plain(suggested),
            'recipe': recipe.id if recipe else None,
            'batches': batches, 'batch_size': _plain(recipe.yield_quantity) if recipe else None,
        })
    return {'target': target.isoformat(), 'weeks_with_data': weeks,
            'rows': sorted(rows, key=lambda r: Decimal(r['suggested']), reverse=True)}
