"""
Registrar una merma: sale del inventario al costo promedio vigente (una transacción).
Lo que se vende por unidad se pierde en unidades enteras.
"""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.core.inventory import services as inventory
from gestorpro.core.inventory.models import StockMovement
from gestorpro.kernel.money import money_str
from gestorpro.kernel.units import quantity as to_quantity

from .models import WasteReason, WasteRecord

DEFAULT_REASONS = [
    ('unsold', 'Sobrante del día'),
    ('burnt', 'Quemado o mal horneado'),
    ('expired', 'Vencido'),
    ('damaged', 'Dañado o caído'),
    ('tasting', 'Degustación'),
    ('staff', 'Consumo del personal'),
]


def ensure_default_reasons() -> None:
    for sort, (code, name) in enumerate(DEFAULT_REASONS):
        WasteReason.objects.get_or_create(code=code, defaults={'name': name, 'sort': sort})


@transaction.atomic
def register_waste(*, user, item_id: int, quantity, reason: WasteReason, notes: str = '', location=None) -> WasteRecord:
    if not reason.is_active:
        raise ValidationError({'reason': 'Motivo inactivo.'})
    location = location or inventory.default_location()
    item = inventory.lock_items([item_id]).get(item_id)
    if item is None:
        raise ValidationError({'item': 'El ítem no existe.'})
    if not item.tracks_stock:
        raise ValidationError({'item': f'«{item.name}» no maneja existencias.'})
    qty = to_quantity(quantity)
    if qty <= 0:
        raise ValidationError({'quantity': 'La cantidad debe ser mayor que cero.'})
    if item.unit.code == 'und' and qty != qty.to_integral_value():
        raise ValidationError({'quantity': f'«{item.name}» se cuenta en unidades enteras.'})
    record = WasteRecord.objects.create(location=location, item=item, quantity=qty, reason=reason,
                                        unit_cost=item.avg_cost, total_cost=qty * item.avg_cost,
                                        notes=(notes or '')[:200], created_by=user)
    inventory.post(item=item, location=location, type=StockMovement.Type.WASTE, quantity=qty, user=user,
                   source=inventory.Source('waste', record.id, f'Merma: {reason.name}'), reason=notes)
    audit.record('waste.record.created', target=record,
                 summary=f'Merma de {qty.normalize()} {item.unit.symbol} de {item.name} ({reason.name}, '
                         f'${money_str(record.total_cost)})')
    return record
