"""
Servicio de facturación.

Reglas que el backend garantiza, sin importar lo que envíe el frontend:
- Precio e impuesto salen del catálogo. Un precio distinto exige el permiso
  `billing.override_price`; el impuesto nunca lo define el cliente.
- Descuentos exigen `billing.apply_discount` y no pueden superar el total.
- Los totales se calculan en servidor con Decimal y redondeo comercial.
- Un documento pagado o cancelado no puede cambiar su contenido económico,
  y las transiciones de estado siguen Invoice.ALLOWED_TRANSITIONS (pagada y
  cancelada son estados finales).
- Todo ocurre en una transacción con bloqueo de la factura: o se guarda
  completo o no se guarda nada.
"""
from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from gestorpro.core.audit import services as audit
from gestorpro.kernel.money import ZERO, money, percentage_of, to_decimal

from .models import Invoice, InvoiceLine


def _build_line(position, data, membership):
    product = data['product']
    if not product.is_active:
        raise ValidationError({'items': f'El producto "{product.name}" está inactivo.'})
    if not product.is_sellable:
        raise ValidationError({'items': f'"{product.name}" es un ingrediente que no se vende.'})
    unit_price = money(product.price)
    requested = data.get('unit_price')
    if requested is not None and money(requested) != unit_price:
        if not membership.has_perm('billing.override_price'):
            raise ValidationError({'items': f'No tienes permiso para cambiar el precio de "{product.name}".'})
        unit_price = money(requested)
    quantity = to_decimal(data['quantity'])
    line_subtotal = money(quantity * unit_price)
    tax_amount = percentage_of(line_subtotal, product.tax_rate)
    return InvoiceLine(
        product=product, description=data.get('description', '') or product.name,
        quantity=quantity, unit_price=unit_price, tax_rate=product.tax_rate,
        line_subtotal=line_subtotal, tax_amount=tax_amount, line_total=line_subtotal + tax_amount,
        position=position,
    )


@transaction.atomic
def save_invoice(*, membership, user, header: dict, lines: list[dict] | None, invoice: Invoice | None = None):
    if invoice is None:
        if not lines:
            raise ValidationError({'items': 'El documento necesita al menos una línea.'})
        invoice = Invoice(created_by=user)
        previous_discount = ZERO
        before = None
    else:
        invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
        previous_discount = invoice.discount
        before = audit.snapshot(invoice)
        economic_change = lines is not None or ('discount' in header and money(header['discount']) != invoice.discount)
        if invoice.status in Invoice.LOCKED_STATUSES and economic_change:
            raise ValidationError('Un documento pagado o cancelado no puede modificarse.')
        new_status = header.get('status', invoice.status)
        if new_status != invoice.status and new_status not in Invoice.ALLOWED_TRANSITIONS[invoice.status]:
            labels = dict(Invoice.Status.choices)
            raise ValidationError(
                {'status': f'No se puede pasar de «{labels[invoice.status]}» a «{labels[new_status]}».'})

    for field, value in header.items():
        setattr(invoice, field, value)
    invoice.discount = money(invoice.discount or ZERO)
    if invoice.discount != previous_discount and invoice.discount > ZERO \
            and not membership.has_perm('billing.apply_discount'):
        raise PermissionDenied('No tienes permiso para aplicar descuentos.')
    invoice.save()

    if lines is not None:
        if not lines:
            raise ValidationError({'items': 'El documento necesita al menos una línea.'})
        invoice.lines.all().delete()
        new_lines = [_build_line(position, data, membership) for position, data in enumerate(lines)]
        for line in new_lines:
            line.invoice = invoice
        InvoiceLine.objects.bulk_create(new_lines)

    totals = invoice.lines.aggregate(subtotal=Sum('line_subtotal'), tax=Sum('tax_amount'))
    invoice.subtotal = money(totals['subtotal'] or ZERO)
    invoice.tax_amount = money(totals['tax'] or ZERO)
    if invoice.discount > invoice.subtotal + invoice.tax_amount:
        raise ValidationError({'discount': 'El descuento no puede superar el total del documento.'})
    invoice.total = invoice.subtotal + invoice.tax_amount - invoice.discount
    invoice.save(update_fields=['subtotal', 'tax_amount', 'total', 'updated_at'])
    _audit_save(invoice, before, lines_replaced=lines is not None)
    return invoice


def _audit_save(invoice, before, lines_replaced):
    label = f'{invoice.get_invoice_type_display().lower()} {invoice.number}'
    if before is None:
        audit.record('billing.invoice.created', target=invoice,
                     summary=f'Creó la {label} por {invoice.total}',
                     changes=audit.diff({}, audit.snapshot(invoice)))
        return
    changes = audit.diff(before, audit.snapshot(invoice))
    if lines_replaced:
        changes['lines'] = ['reemplazadas', 'reemplazadas']
    if not changes:
        return
    audit.record('billing.invoice.updated', target=invoice, summary=f'Modificó la {label}', changes=changes)
    if 'status' in changes:
        old, new = changes['status']
        labels = dict(Invoice.Status.choices)
        audit.record('billing.invoice.status_changed', target=invoice, changes={'status': [old, new]},
                     summary=f'Cambió el estado de la {label}: {labels.get(old, old)} → {labels.get(new, new)}')


@transaction.atomic
def delete_invoice(invoice: Invoice):
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.invoice_type == Invoice.InvoiceType.INVOICE and invoice.status != Invoice.Status.DRAFT:
        raise ValidationError('Solo se pueden eliminar borradores. Cancela la factura en su lugar.')
    before, pk = audit.snapshot(invoice), invoice.pk
    invoice.delete()
    audit.record_deleted(invoice, before, pk)
