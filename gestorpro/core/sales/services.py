"""
Servicio de ventas del POS. Reglas que garantiza el backend, sin importar lo
que envíe el navegador:

- Precio, IVA y costo salen del catálogo en el momento de vender. El POS no
  acepta precios del cliente.
- Solo se venden ítems activos y vendibles. Lo que se vende por unidad exige
  cantidades enteras.
- Un descuento exige el permiso `sales.discount` y no puede superar el total.
- Hace falta un turno de caja abierto de quien vende.
- Los pagos deben cubrir el total exacto. Solo el efectivo admite recibir de
  más (se calcula el cambio); tarjeta o transferencia por encima del total
  se rechaza.
- Todo ocurre en UNA transacción: número consecutivo, venta, líneas, pagos,
  movimiento de caja, descuento de existencias y auditoría. O todo o nada.
- `client_uuid` hace la operación idempotente: un reintento devuelve la
  misma venta en lugar de crear otra.
- Anular exige `sales.void`, un motivo y que el turno de caja de la venta siga
  abierto (después del cierre, la corrección será una devolución). Devuelve el
  efectivo y las existencias; la venta nunca se borra.

Existencias (transitorio hasta la Fase 8): la venta descuenta `Item.stock` y
la anulación lo repone. Se permite quedar en negativo (en panadería se vende
antes de registrar la producción); la Fase 8 convertirá cada línea en un
movimiento del libro de inventario.
"""
from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.core.cash.models import CashMovement, CashSession
from gestorpro.core.cash.services import current_session
from gestorpro.core.catalog.models import Item
from gestorpro.core.customers.services import ensure_final_consumer
from gestorpro.core.numbering.services import next_number
from gestorpro.kernel.money import ZERO, money, money_str, percentage_of
from gestorpro.kernel.units import quantity as to_quantity

from .models import Payment, PaymentMethod, Sale, SaleLine

SALE_DOC = 'sale'
SALE_PREFIX = 'V'


def _build_lines(raw_lines: list[dict]) -> list[SaleLine]:
    if not raw_lines:
        raise ValidationError({'lines': 'La venta no tiene productos.'})
    # Varias líneas del mismo ítem se agrupan (el POS puede enviar el mismo producto dos veces)
    grouped: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for raw in raw_lines:
        qty = to_quantity(raw['quantity'])
        if qty <= 0:
            raise ValidationError({'lines': 'Las cantidades deben ser mayores que cero.'})
        grouped[raw['item']] += qty
    items = {i.id: i for i in Item.objects.select_related('unit').filter(id__in=grouped)}
    lines = []
    for item_id, qty in grouped.items():
        item = items.get(item_id)
        if item is None:
            raise ValidationError({'lines': 'Uno de los productos no existe.'})
        if not item.is_active or not item.is_sellable:
            raise ValidationError({'lines': f'«{item.name}» no está disponible para la venta.'})
        if item.unit.code == 'und' and qty != qty.to_integral_value():
            raise ValidationError({'lines': f'«{item.name}» se vende por unidades enteras.'})
        subtotal = money(qty * item.price)
        tax = percentage_of(subtotal, item.tax_rate)
        lines.append(SaleLine(item=item, item_name=item.name, unit_symbol=item.unit.symbol, quantity=qty,
                              unit_price=item.price, tax_rate=item.tax_rate, line_subtotal=subtotal,
                              tax_amount=tax, line_total=subtotal + tax, unit_cost=item.avg_cost))
    return lines


def _build_payments(raw_payments: list[dict], total: Decimal) -> tuple[list[Payment], Decimal]:
    if not raw_payments:
        raise ValidationError({'payments': 'Indica cómo paga el cliente.'})
    methods = {m.id: m for m in PaymentMethod.objects.filter(id__in=[p['method'] for p in raw_payments])}
    payments, tendered_total, cash_tendered = [], ZERO, ZERO
    for raw in raw_payments:
        method = methods.get(raw['method'])
        if method is None or not method.is_active:
            raise ValidationError({'payments': 'Medio de pago no disponible.'})
        tendered = money(raw['amount'])
        if tendered <= 0:
            raise ValidationError({'payments': 'Los pagos deben ser mayores que cero.'})
        tendered_total += tendered
        if method.affects_cash_drawer:
            cash_tendered += tendered
        payments.append(Payment(method=method, amount=tendered, tendered=tendered,
                                reference=(raw.get('reference') or '')[:60]))
    if tendered_total < total:
        raise ValidationError({'payments': f'Faltan ${money_str(total - tendered_total)} por pagar.'})
    change = tendered_total - total
    if change > cash_tendered:
        raise ValidationError({'payments': 'Solo el efectivo puede superar el total (para dar cambio).'})
    # El cambio se descuenta del efectivo: lo aplicado al pago es lo que realmente queda en caja
    remaining = change
    for payment in reversed(payments):
        if remaining and payment.method.affects_cash_drawer:
            applied = min(remaining, payment.amount)
            payment.amount -= applied
            remaining -= applied
    return [p for p in payments if p.amount > 0], change


@transaction.atomic
def complete_sale(*, membership, client_uuid, lines: list[dict], payments: list[dict],
                  customer=None, discount=None) -> tuple[Sale, bool]:
    """Registra una venta. Devuelve (venta, creada). Si `client_uuid` ya existe, devuelve la existente."""
    existing = Sale.objects.filter(client_uuid=client_uuid).first()
    if existing is not None:
        if existing.cashier_id != membership.user_id:
            raise ValidationError('Identificador de venta repetido.')
        return existing, False

    session = current_session(membership.user)
    if session is None:
        raise ValidationError('Abre tu turno de caja antes de vender.')
    session = CashSession.objects.select_for_update().select_related('register').get(pk=session.pk)
    if not session.is_open:
        raise ValidationError('Tu turno de caja está cerrado.')

    sale_lines = _build_lines(lines)
    subtotal = sum((line.line_subtotal for line in sale_lines), ZERO)
    tax_total = sum((line.tax_amount for line in sale_lines), ZERO)
    gross = subtotal + tax_total
    discount_value = money(discount or 0)
    if discount_value:
        if not membership.has_perm('sales.discount'):
            raise PermissionDenied('No tienes permiso para aplicar descuentos.')
        if discount_value < 0 or discount_value > gross:
            raise ValidationError({'discount': 'El descuento no puede ser negativo ni mayor que el total.'})
    total = gross - discount_value
    sale_payments, change = _build_payments(payments, total)

    location = session.register.location
    try:
        with transaction.atomic():
            sale = Sale.objects.create(
                number=next_number(location=location, doc_type=SALE_DOC, prefix=SALE_PREFIX),
                location=location, cash_session=session, customer=customer or ensure_final_consumer(),
                cashier=membership.user, client_uuid=client_uuid, subtotal=subtotal, tax_total=tax_total,
                discount=discount_value, total=total, change_given=change,
                cost_total=sum((line.unit_cost * line.quantity for line in sale_lines), Decimal('0')),
            )
    except IntegrityError as exc:  # el mismo client_uuid llegó dos veces a la vez
        raise ValidationError('Esta venta ya se está registrando.') from exc

    for line in sale_lines:
        line.sale = sale
    SaleLine.objects.bulk_create(sale_lines)
    for payment in sale_payments:
        payment.sale = sale
    Payment.objects.bulk_create(sale_payments)

    cash_in = sum((p.amount for p in sale_payments if p.method.affects_cash_drawer), ZERO)
    if cash_in > 0:
        CashMovement.objects.create(session=session, type=CashMovement.Type.SALE, amount=cash_in, sale=sale,
                                    created_by=membership.user)
    for line in sale_lines:
        if line.item.tracks_stock:
            Item.objects.filter(pk=line.item_id).update(stock=F('stock') - line.quantity)

    audit.record('sales.sale.completed', target=sale,
                 summary=f'Venta {sale.number} por ${money_str(total)} ({len(sale_lines)} producto(s))')
    return sale, True


@transaction.atomic
def void_sale(*, membership, sale: Sale, reason: str) -> Sale:
    if not membership.has_perm('sales.void'):
        raise PermissionDenied('No tienes permiso para anular ventas.')
    sale = Sale.objects.select_for_update().select_related('cash_session').get(pk=sale.pk)
    if sale.status == Sale.Status.VOIDED:
        raise ValidationError('La venta ya está anulada.')
    reason = (reason or '').strip()
    if not reason:
        raise ValidationError({'reason': 'Indica el motivo de la anulación.'})
    session = CashSession.objects.select_for_update().get(pk=sale.cash_session_id)
    if not session.is_open:
        raise ValidationError('El turno de caja de esta venta ya se cerró; no se puede anular.')

    cash_paid = sum((p.amount for p in sale.payments.select_related('method') if p.method.affects_cash_drawer), ZERO)
    if cash_paid > 0:
        CashMovement.objects.create(session=session, type=CashMovement.Type.VOID, amount=-cash_paid, sale=sale,
                                    reason=reason[:200], created_by=membership.user)
    for line in sale.lines.select_related('item'):
        if line.item.tracks_stock:
            Item.objects.filter(pk=line.item_id).update(stock=F('stock') + line.quantity)

    sale.status = Sale.Status.VOIDED
    sale.voided_at, sale.voided_by, sale.void_reason = timezone.now(), membership.user, reason[:200]
    sale.save(update_fields=['status', 'voided_at', 'voided_by', 'void_reason', 'updated_at'])
    audit.record('sales.sale.voided', target=sale,
                 summary=f'Anuló la venta {sale.number} (${money_str(sale.total)}): {reason}')
    return sale


DEFAULT_PAYMENT_METHODS = [
    ('cash', 'Efectivo', PaymentMethod.Kind.CASH),
    ('card', 'Tarjeta', PaymentMethod.Kind.CARD),
    ('nequi', 'Nequi', PaymentMethod.Kind.WALLET),
    ('daviplata', 'Daviplata', PaymentMethod.Kind.WALLET),
    ('transfer', 'Transferencia', PaymentMethod.Kind.TRANSFER),
]


def ensure_pos_defaults() -> None:
    """Medios de pago y una caja por sucursal. Requiere el tenant activo; idempotente."""
    from gestorpro.core.cash.models import CashRegister
    from gestorpro.core.tenancy.models import Location

    for sort, (code, name, kind) in enumerate(DEFAULT_PAYMENT_METHODS):
        PaymentMethod.objects.get_or_create(code=code, defaults={'name': name, 'kind': kind, 'sort': sort})
    for location in Location.objects.filter(is_active=True):
        if not CashRegister.objects.filter(location=location).exists():
            CashRegister.objects.create(location=location, name='Caja principal')
