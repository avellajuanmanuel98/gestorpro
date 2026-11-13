"""
Servicio del libro de inventario. ÚNICA forma de cambiar existencias.

Costo promedio ponderado móvil (documentado en docs/miga/07-fase-8-inventario.md):

  - Entrada CON costo (compra, producción, saldo inicial, devolución de venta):
        nuevo_promedio = (existencia × promedio + cantidad × costo_entrada)
                         / (existencia + cantidad)
    Si la existencia previa es cero o negativa, el nuevo promedio es el costo
    de la entrada (no tiene sentido promediar contra un faltante).
  - Salida (venta, consumo, merma, faltante): sale al costo promedio VIGENTE,
    que queda congelado en el movimiento. El promedio no cambia.
  - Sobrante de un conteo sin costo: entra al promedio vigente.

Concurrencia: los ítems afectados se bloquean (SELECT … FOR UPDATE, en orden de
id para evitar interbloqueos) dentro de la transacción del documento.

Se permite existencia negativa: en panadería se vende antes de registrar la
producción. Queda visible como alerta y el conteo físico la corrige.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from gestorpro.core.catalog.models import Item
from gestorpro.core.tenancy.models import Location
from gestorpro.kernel.units import quantity as to_quantity

from .models import StockLevel, StockMovement

COST = Decimal('0.0001')


def _cost(value) -> Decimal:
    return Decimal(value).quantize(COST, rounding=ROUND_HALF_UP)


def default_location() -> Location:
    location = Location.objects.filter(is_default=True).first() or Location.objects.order_by('id').first()
    if location is None:
        raise ValidationError('La empresa no tiene sucursales.')
    return location


def lock_items(ids) -> dict[int, Item]:
    """Bloquea los ítems (en orden de id) y los devuelve frescos."""
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError('lock_items() requiere una transacción activa.')
    return {i.id: i for i in Item.objects.select_for_update().select_related('unit')
            .filter(id__in=set(ids)).order_by('id')}


@dataclass
class Source:
    type: str = ''
    id: int | None = None
    label: str = ''


def post(*, item: Item, location: Location, type: str, quantity, user, unit_cost=None,
         source: Source | None = None, reason: str = '') -> StockMovement:
    """
    Registra un movimiento y actualiza existencia y costo promedio.
    `item` debe venir bloqueado (lock_items) dentro de la transacción del documento.
    `quantity` es positiva; el signo lo decide el tipo.
    """
    if not item.tracks_stock:
        raise ValidationError(f'«{item.name}» no maneja existencias.')
    qty = to_quantity(quantity)
    if qty <= 0:
        raise ValidationError('La cantidad debe ser mayor que cero.')
    inbound = type in StockMovement.INBOUND
    signed = qty if inbound else -qty

    stock_before, avg_before = item.stock, item.avg_cost
    if inbound and unit_cost is not None:
        cost = _cost(unit_cost)
        if cost < 0:
            raise ValidationError('El costo no puede ser negativo.')
        new_avg = cost if stock_before <= 0 else _cost((stock_before * avg_before + qty * cost) / (stock_before + qty))
    else:
        cost, new_avg = avg_before, avg_before

    level, _ = StockLevel.objects.get_or_create(item=item, location=location)
    level = StockLevel.objects.select_for_update().get(pk=level.pk)
    level.quantity += signed
    level.save(update_fields=['quantity', 'updated_at'])

    item.stock = stock_before + signed
    item.avg_cost = new_avg
    Item.objects.filter(pk=item.pk).update(stock=item.stock, avg_cost=item.avg_cost)

    src = source or Source()
    return StockMovement.objects.create(
        item=item, location=location, type=type, quantity=signed, unit_cost=cost, total_cost=_cost(signed * cost),
        balance_after=item.stock, avg_cost_after=new_avg, source_type=src.type, source_id=src.id,
        source_label=src.label[:60], reason=(reason or '')[:200], created_by=user,
    )


# ── Descarga por receta (la registra la capability de producción) ───────────

_recipe_resolver = None


def set_recipe_resolver(fn) -> None:
    """
    fn(product: Item, quantity: Decimal) -> list[tuple[Item, Decimal]] | None
    Devuelve los ingredientes (en su unidad) que consume vender `quantity` del
    producto, o None si no tiene receta activa. El Core no conoce las recetas.
    """
    global _recipe_resolver
    _recipe_resolver = fn


def recipe_consumption(product: Item, quantity) -> list[tuple[Item, Decimal]] | None:
    return _recipe_resolver(product, quantity) if _recipe_resolver else None


@transaction.atomic
def physical_count(*, user, location: Location, counts: list[dict], note: str = '') -> list[StockMovement]:
    """
    Conteo físico: para cada ítem, la diferencia entre lo contado y lo que dice
    el sistema en esa sucursal se registra como ajuste (sobrante o faltante).
    """
    from gestorpro.core.audit import services as audit

    if not counts:
        raise ValidationError({'counts': 'No hay ítems contados.'})
    items = lock_items([c['item'] for c in counts])
    movements = []
    for count in counts:
        item = items.get(count['item'])
        if item is None:
            raise ValidationError({'counts': 'Uno de los ítems no existe.'})
        counted = to_quantity(count['counted'])
        if counted < 0:
            raise ValidationError({'counts': f'«{item.name}»: el conteo no puede ser negativo.'})
        level = StockLevel.objects.filter(item=item, location=location).first()
        current = level.quantity if level else Decimal('0')
        diff = counted - current
        if diff == 0:
            continue
        movements.append(post(
            item=item, location=location, type=(StockMovement.Type.ADJUSTMENT_IN if diff > 0
                                                else StockMovement.Type.ADJUSTMENT_OUT),
            quantity=abs(diff), user=user, source=Source('count', None, 'Conteo físico'),
            reason=note or 'Conteo físico'))
    audit.record('inventory.count.applied', entity_type='inventory.count',
                 summary=f'Conteo físico en {location.name}: {len(movements)} ajuste(s) de {len(counts)} ítem(s)')
    return movements
