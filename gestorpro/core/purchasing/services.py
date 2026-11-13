"""
Registrar una compra (una sola transacción):

- Cada línea se convierte de la unidad de compra a la del ítem (kernel/units);
  convertir entre dimensiones distintas (kg → l) se rechaza.
- El total lo calcula el servidor: cantidad × costo, redondeado a pesos con centavos.
- Entra al libro de inventario como "Compra" y actualiza el costo promedio ponderado.
- Solo ítems que manejan existencias (no servicios ni bebidas preparadas).
"""
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.core.catalog.models import UnitOfMeasure
from gestorpro.core.inventory import services as inventory
from gestorpro.core.inventory.models import StockMovement
from gestorpro.core.numbering.services import next_number
from gestorpro.kernel.money import ZERO, money, money_str
from gestorpro.kernel.units import IncompatibleUnits, convert
from gestorpro.kernel.units import quantity as to_quantity

from .models import PurchaseLine, PurchaseReceipt


@transaction.atomic
def register_purchase(*, user, lines: list[dict], received_on, supplier=None, supplier_invoice='', notes='',
                      location=None) -> PurchaseReceipt:
    if not lines:
        raise ValidationError({'lines': 'La compra no tiene ítems.'})
    location = location or inventory.default_location()
    items = inventory.lock_items([line['item'] for line in lines])
    units = {u.code: u for u in UnitOfMeasure.objects.all()}

    prepared = []
    for raw in lines:
        item = items.get(raw['item'])
        if item is None:
            raise ValidationError({'lines': 'Uno de los ítems no existe.'})
        if not item.tracks_stock:
            raise ValidationError({'lines': f'«{item.name}» no maneja existencias.'})
        unit = units.get(raw.get('unit') or item.unit.code)
        if unit is None:
            raise ValidationError({'lines': 'Unidad desconocida.'})
        qty = to_quantity(raw['quantity'])
        cost = Decimal(raw['unit_cost'])
        if qty <= 0 or cost < 0:
            raise ValidationError({'lines': f'«{item.name}»: cantidad y costo deben ser positivos.'})
        try:
            base_qty = convert(qty, unit.as_unit(), item.unit.as_unit())
        except IncompatibleUnits as exc:
            raise ValidationError({'lines': f'«{item.name}» se maneja en {item.unit.name.lower()}; '
                                            f'no se puede comprar en {unit.name.lower()}.'}) from exc
        total = money(qty * cost)
        base_cost = (total / base_qty).quantize(Decimal('0.0001'))
        prepared.append(PurchaseLine(item=item, quantity=qty, unit=unit, unit_cost=cost, total=total,
                                     base_quantity=base_qty, base_unit_cost=base_cost))

    receipt = PurchaseReceipt.objects.create(
        number=next_number(location=location, doc_type='purchase', prefix='C'), location=location,
        supplier=supplier, supplier_invoice=(supplier_invoice or '')[:60], received_on=received_on,
        total=sum((p.total for p in prepared), ZERO), notes=notes or '', created_by=user)
    for line in prepared:
        line.receipt = receipt
    PurchaseLine.objects.bulk_create(prepared)

    source = inventory.Source('purchase', receipt.id, f'Compra {receipt.number}')
    for line in prepared:
        inventory.post(item=line.item, location=location, type=StockMovement.Type.PURCHASE,
                       quantity=line.base_quantity, unit_cost=line.base_unit_cost, user=user, source=source)
    who = f' a {supplier}' if supplier else ''
    audit.record('purchasing.receipt.created', target=receipt,
                 summary=f'Registró la compra {receipt.number}{who} por ${money_str(receipt.total)}')
    return receipt
