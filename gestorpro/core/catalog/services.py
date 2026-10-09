"""
Reglas del catálogo que el backend garantiza sin importar lo que envíe el cliente.

- El `kind` decide qué campos tienen sentido:
  * Productos (elaborado, reventa, servicio) siempre se venden y necesitan precio.
  * Un ingrediente solo tiene precio si se marca como vendible; si no, precio e
    IVA se ignoran y quedan en 0.
  * Un servicio no tiene existencias ni costo de inventario, y se mide en unidades.
- La categoría debe ser del mismo tipo que el ítem (de productos o de ingredientes).
- El código (SKU) se genera si no se indica: PRD-0001, ING-0001…
- El límite `products` del plan cuenta solo productos; los ingredientes no consumen cupo.
"""
import re
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from .models import Category, Item, UnitOfMeasure

CODE_PREFIX = {
    Item.Kind.FINISHED_GOOD: 'PRD',
    Item.Kind.RESALE: 'PRD',
    Item.Kind.SERVICE: 'SRV',
    Item.Kind.RAW_MATERIAL: 'ING',
}


def category_kind_for(kind: str) -> str:
    return Category.Kind.INGREDIENT if kind == Item.Kind.RAW_MATERIAL else Category.Kind.PRODUCT


def next_code(kind: str) -> str:
    prefix = CODE_PREFIX[kind]
    pattern = re.compile(rf'^{prefix}-(\d+)$')
    numbers = [int(m.group(1)) for code in Item.objects.filter(code__startswith=f'{prefix}-')
               .values_list('code', flat=True) if (m := pattern.match(code))]
    return f'{prefix}-{(max(numbers) + 1) if numbers else 1:04d}'


def normalize(data: dict, instance: Item | None = None) -> dict:
    """Ajusta y valida los datos de un ítem antes de guardarlo. Devuelve los datos a guardar."""
    get = lambda key, default=None: data.get(key, getattr(instance, key, default) if instance else default)  # noqa: E731
    kind = data['kind'] = get('kind', Item.Kind.FINISHED_GOOD)
    errors = {}

    if instance is not None and 'kind' in data and data['kind'] != instance.kind:
        moving_between_screens = (instance.kind == Item.Kind.RAW_MATERIAL) != (kind == Item.Kind.RAW_MATERIAL)
        if moving_between_screens and instance.invoice_lines.exists():
            errors['kind'] = 'Este ítem ya aparece en documentos; no puede cambiar entre producto e ingrediente.'

    # Vendible
    if kind in Item.PRODUCT_KINDS:
        data['is_sellable'] = True
    elif 'is_sellable' not in data and (instance is None or instance.kind != kind):
        data['is_sellable'] = False  # un ingrediente nuevo no se vende salvo que se indique
    sellable = get('is_sellable')
    if sellable:
        if Decimal(get('price', 0) or 0) <= 0:
            errors['price'] = 'Indica el precio de venta.'
    else:
        data['price'] = Decimal('0')
        data['tax_rate'] = Decimal('0')

    # Servicios: sin existencias ni costo de inventario, siempre por unidad
    unit = get('unit')
    if kind == Item.Kind.SERVICE:
        data.update(stock=Decimal('0'), minimum_stock=Decimal('0'), avg_cost=Decimal('0'))
        und = UnitOfMeasure.objects.get(code='und')
        if unit is not None and unit != und:
            errors['unit'] = 'Un servicio se vende por unidad.'
        data['unit'] = unit = und
    if unit is None:  # al crear, por defecto se vende por unidad
        data['unit'] = unit = UnitOfMeasure.objects.get(code='und')

    category = get('category')
    if category is not None and category.kind != category_kind_for(kind):
        expected = 'ingredientes' if kind == Item.Kind.RAW_MATERIAL else 'productos'
        errors['category'] = f'Elige una categoría de {expected}.'

    code = (get('code') or '').strip()
    if code:
        data['code'] = code
        clash = Item.objects.filter(code__iexact=code)
        if instance is not None:
            clash = clash.exclude(pk=instance.pk)
        if clash.exists():
            errors['code'] = 'Ya existe un ítem con este código.'

    if errors:
        raise ValidationError(errors)

    if not code:
        data['code'] = next_code(kind)
    return data


def products_count() -> int:
    """Consumo del límite `products` del plan: solo lo que se gestiona como producto."""
    return Item.objects.filter(kind__in=Item.PRODUCT_KINDS).count()
