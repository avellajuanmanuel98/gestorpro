"""
Servicios de recetas y producción. Reglas que garantiza el backend:

Recetas
- Solo para productos elaborados; los ingredientes deben manejar existencias.
- Cada cantidad se expresa en una unidad de la MISMA dimensión que el
  ingrediente (gramos de harina que se maneja en kg: sí; litros: no).
- Un ingrediente no puede ser el mismo producto (receta circular directa).
- Si la versión activa ya se usó en producción, guardar cambios crea una
  versión nueva y desactiva la anterior; si no, se edita en el lugar.

Costo estimado de una receta (al costo promedio vigente de cada ingrediente):
    cantidad_en_unidad_del_ingrediente × (1 + desperdicio %) × costo_promedio
    costo_unitario = Σ / rendimiento

Producción (una transacción)
- Lo planificado = receta × (cantidad a producir / rendimiento).
- Se consume lo REAL (si se indica) o lo planificado, al costo promedio vigente.
- El producto entra con costo = Σ consumos / cantidad producida, que se
  promedia con su existencia (promedio ponderado).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.core.catalog.models import Item, UnitOfMeasure
from gestorpro.core.inventory import services as inventory
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.numbering.services import next_number
from gestorpro.kernel.money import money_str
from gestorpro.kernel.units import IncompatibleUnits, convert
from gestorpro.kernel.units import quantity as to_quantity

from .models import ProductionBatch, ProductionConsumption, Recipe, RecipeLine

Q4 = Decimal('0.0001')
HUNDRED = Decimal('100')


def _q(value) -> Decimal:
    return Decimal(value).quantize(Q4, rounding=ROUND_HALF_UP)


def line_base_quantity(line: RecipeLine) -> Decimal:
    """Cantidad de la línea en la unidad del ingrediente, con su desperdicio."""
    base = convert(line.quantity, line.unit.as_unit(), line.ingredient.unit.as_unit())
    return _q(base * (1 + line.waste_pct / HUNDRED))


def recipe_cost(recipe: Recipe) -> dict:
    lines = []
    total = Decimal('0')
    for line in recipe.lines.select_related('ingredient__unit', 'unit'):
        qty = line_base_quantity(line)
        cost = _q(qty * line.ingredient.avg_cost)
        total += cost
        lines.append({'line': line, 'base_quantity': qty, 'cost': cost, 'missing_cost': line.ingredient.avg_cost <= 0})
    unit_cost = _q(total / recipe.yield_quantity)
    price = recipe.product.price
    margin = (((price - unit_cost) / price * HUNDRED).quantize(Decimal('0.1')) if price > 0 and total > 0 else None)
    return {'lines': lines, 'total': _q(total), 'unit_cost': unit_cost, 'margin_pct': margin,
            'complete': all(not entry['missing_cost'] for entry in lines)}


def scaled_needs(recipe: Recipe, quantity) -> list[tuple[Item, Decimal]]:
    factor = to_quantity(quantity) / recipe.yield_quantity
    return [(line.ingredient, _q(line_base_quantity(line) * factor))
            for line in recipe.lines.select_related('ingredient__unit', 'unit')]


def active_recipe(product: Item) -> Recipe | None:
    return Recipe.objects.filter(product=product, is_active=True).first()


def resolve_sale_consumption(product: Item, quantity):
    """Proveedor para el Core (ventas de productos con `consume_on_sale`)."""
    recipe = active_recipe(product)
    return scaled_needs(recipe, quantity) if recipe else None


@transaction.atomic
def save_recipe(*, user, product: Item, yield_quantity, lines: list[dict], notes: str = '') -> Recipe:
    if product.kind != Item.Kind.FINISHED_GOOD:
        raise ValidationError({'product': 'Las recetas son para productos elaborados.'})
    yield_qty = to_quantity(yield_quantity)
    if yield_qty <= 0:
        raise ValidationError({'yield_quantity': 'El rendimiento debe ser mayor que cero.'})
    if product.unit.code == 'und' and yield_qty != yield_qty.to_integral_value():
        raise ValidationError({'yield_quantity': 'El rendimiento en unidades debe ser entero.'})
    if not lines:
        raise ValidationError({'lines': 'La receta necesita al menos un ingrediente.'})

    ids = [ln['ingredient'] for ln in lines]
    ingredients = {i.id: i for i in Item.objects.select_related('unit').filter(id__in=ids)}
    units = {u.code: u for u in UnitOfMeasure.objects.all()}
    seen, prepared = set(), []
    for sort, raw in enumerate(lines):
        ing = ingredients.get(raw['ingredient'])
        if ing is None:
            raise ValidationError({'lines': 'Uno de los ingredientes no existe.'})
        if ing.id == product.id:
            raise ValidationError({'lines': 'Un producto no puede ser ingrediente de sí mismo.'})
        if not ing.tracks_stock:
            raise ValidationError({'lines': f'«{ing.name}» no maneja existencias; no puede ser ingrediente.'})
        if ing.id in seen:
            raise ValidationError({'lines': f'«{ing.name}» está repetido.'})
        seen.add(ing.id)
        unit = units.get(raw.get('unit') or ing.unit.code)
        if unit is None:
            raise ValidationError({'lines': 'Unidad desconocida.'})
        try:
            convert(1, unit.as_unit(), ing.unit.as_unit())
        except IncompatibleUnits as exc:
            raise ValidationError({'lines': f'«{ing.name}» se maneja en {ing.unit.name.lower()}; '
                                            f'no se puede medir en {unit.name.lower()}.'}) from exc
        qty = to_quantity(raw['quantity'])
        waste = Decimal(raw.get('waste_pct') or 0)
        if qty <= 0 or not (0 <= waste <= 100):
            raise ValidationError({'lines': f'«{ing.name}»: revisa la cantidad y el desperdicio.'})
        prepared.append(RecipeLine(ingredient=ing, quantity=qty, unit=unit, waste_pct=waste, sort=sort))

    current = Recipe.objects.select_for_update().filter(product=product, is_active=True).first()
    if current is not None and not current.batches.exists():
        recipe = current
        recipe.yield_quantity, recipe.notes = yield_qty, notes or ''
        recipe.save(update_fields=['yield_quantity', 'notes', 'updated_at'])
        recipe.lines.all().delete()
        action = 'actualizó'
    else:
        version = (Recipe.objects.filter(product=product).order_by('-version').values_list('version', flat=True)
                   .first() or 0) + 1
        if current is not None:
            current.is_active = False
            current.save(update_fields=['is_active', 'updated_at'])
        recipe = Recipe.objects.create(product=product, version=version, yield_quantity=yield_qty,
                                       notes=notes or '', created_by=user)
        action = 'creó' if version == 1 else f'creó la versión {version} de'
    for line in prepared:
        line.recipe = recipe
    RecipeLine.objects.bulk_create(prepared)
    rinde = recipe.yield_quantity.normalize()
    audit.record('production.recipe.saved', target=recipe,
                 summary=f'{action.capitalize()} la receta de {product.name} (rinde {rinde})')
    return recipe


@transaction.atomic
def produce(*, user, recipe: Recipe, quantity, actual: dict[int, object] | None = None, notes: str = '',
            location=None) -> ProductionBatch:
    if not recipe.is_active:
        raise ValidationError('Esa versión de la receta ya no está activa.')
    produced = to_quantity(quantity)
    if produced <= 0:
        raise ValidationError({'quantity': 'Indica cuánto se produjo.'})
    product = recipe.product
    if product.unit.code == 'und' and produced != produced.to_integral_value():
        raise ValidationError({'quantity': f'«{product.name}» se produce en unidades enteras.'})
    location = location or inventory.default_location()

    needs = scaled_needs(recipe, produced)
    actual = {int(k): v for k, v in (actual or {}).items()}
    unknown = set(actual) - {ing.id for ing, _ in needs}
    if unknown:
        raise ValidationError({'actual': 'Solo se pueden ajustar ingredientes de la receta.'})
    locked = inventory.lock_items([product.id] + [ing.id for ing, _ in needs])

    batch = ProductionBatch.objects.create(
        number=next_number(location=location, doc_type='production', prefix='P'), location=location,
        recipe=recipe, product=product, produced_quantity=produced, total_cost=0, unit_cost=0,
        notes=notes or '', created_by=user)
    source = inventory.Source('production', batch.id, f'Producción {batch.number}')
    total = Decimal('0')
    consumptions = []
    for ing, planned in needs:
        used = to_quantity(actual[ing.id]) if ing.id in actual else planned
        if used < 0:
            raise ValidationError({'actual': f'«{ing.name}»: la cantidad no puede ser negativa.'})
        cost = locked[ing.id].avg_cost
        if used > 0:
            inventory.post(item=locked[ing.id], location=location, type=StockMovement.Type.PRODUCTION_CONSUME,
                           quantity=used, user=user, source=source)
        line_total = _q(used * cost)
        total += line_total
        consumptions.append(ProductionConsumption(batch=batch, ingredient=ing, planned_quantity=planned,
                                                  actual_quantity=used, unit_cost=cost, total_cost=line_total))
    ProductionConsumption.objects.bulk_create(consumptions)

    unit_cost = _q(total / produced)
    inventory.post(item=locked[product.id], location=location, type=StockMovement.Type.PRODUCTION_OUTPUT,
                   quantity=produced, unit_cost=unit_cost, user=user, source=source)
    batch.total_cost, batch.unit_cost = _q(total), unit_cost
    batch.save(update_fields=['total_cost', 'unit_cost', 'updated_at'])
    audit.record('production.batch.completed', target=batch,
                 summary=f'Produjo {produced.normalize()} {product.unit.symbol} de {product.name} '
                         f'({batch.number}, costo ${money_str(total)})')
    return batch
